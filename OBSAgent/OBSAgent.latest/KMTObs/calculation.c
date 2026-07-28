////////////////////////////////////////////////////////////////////////////////
////
//// calculation.c 
////   - Astronomical calculation functions with/from USNO NOVAS C codes
////   - NOVAC C codes imported to OBSAgent(v0.8.8) on 2022-10-07
////   - Update
////

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>

////////////////////////////////////////////////////////////////////////////////
////
//// definition/declaration for calculation.c functions
////

//// type definitions

typedef unsigned int UINT;

typedef struct smctime {
  int year;
  int month;
  int day;
  int hour;
  int min;
  double sec;
  UINT secse;  // the time as the number of seconds since the Epoch, 1970-01-01 00:00:00 +0000 (UTC)  //  v0.7.0
} smctime_t;

//// SMC calculation functions

double GetGst(double dJD);
double GetJd(smctime_t ut);
double GetAltitude(double HA, double Dec, double Latitude);
double GetAzimuth (double HA, double Dec, double Latitude);
double GetAirmass(double HA, double Dec, double Latitude);
void GetAltAzmAir(double HA, double Dec, double Latitude, double *Alt, double *Azm, double *Airmass);
void SetSmctime(struct tm tmtime, smctime_t *psmctime);
char trans1060(double dHour, int *pnHour, int *pnMin, double *pdSec, int nDP);

//// from novas.h

/*
   struct ra_of_cio:  right ascension of the Celestial Intermediate
                      Origin (CIO) with respect to the GCRS

   jd_tdb             = TDB Julian date
   ra_cio             = right ascension of the CIO with respect
                        to the GCRS (arcseconds)
*/

   typedef struct
   {
      double jd_tdb;
      double ra_cio;
   } ra_of_cio;

//// from novascon.c

const double T0 = 2451545.00000000;
const double TWOPI = 6.283185307179586476925287;
const double ASEC360 = 1296000.0;
const double ASEC2RAD = 4.848136811095359935899141e-6;
const double DEG2RAD = 0.017453292519943296;
const double RAD2DEG = 57.295779513082321;

//// from novas.c

short int sidereal_time (double jd_high, double jd_low, double delta_t,short int gst_type, short int method, short int accuracy,   double *gst);  // for me
double era (double jd_high, double jd_low);  // for sidereal_time()
void e_tilt (double jd_tdb, short int accuracy,   double *mobl, double *tobl, double *ee, double *dpsi, double *deps);  // for sidereal_time() & nutation() & ira_equinox()
double ee_ct (double jd_high, double jd_low, short int accuracy);  // for e_tilt()
void frame_tie (double *pos1, short int direction,   double *pos2);  // for sidereal_time() & cio_basis()
short int precession (double jd_tdb1, double *pos1, double jd_tdb2,   double *pos2);  // for sidereal_time() & cio_basis()
void nutation (double jd_tdb, short int direction, short int accuracy, double *pos,   double *pos2);  // for sidereal_time() & cio_basis()
void nutation_angles (double t, short int accuracy,   double *dpsi, double *deps);  // for e_tilt()
void fund_args (double t,   double a[5]);  // for ee_ct() & iau2000a() & nu2000k()
double mean_obliq (double jd_tdb);  // for e_tilt()
void tdb2tt (double tdb_jd,   double *tt_jd, double *secdiff);  // for sidereal_time()
short int cio_location (double jd_tdb, short int accuracy,   double *ra_cio, short int *ref_sys);  // for sidereal_time()
short int cio_basis (double jd_tdb, double ra_cio, short int ref_sys, short int accuracy,   double *x, double *y, double *z);  // for sidereal_time()
short int cio_array (double jd_tdb, long int n_pts,   ra_of_cio *cio);  // for cio_location()
double ira_equinox (double jd_tdb, short int equinox, short int accuracy);  // for cio_location()
double julian_date (short int year, short int month, short int day, double hour);  // for me
double norm_ang (double angle);  // for ee_ct()

//// from nutation.c

void iau2000a (double jd_high, double jd_low,   double *dpsi, double *deps);  // for nutation_angles()
void iau2000b (double jd_high, double jd_low,   double *dpsi, double *deps);  // for nutation_angles()
void nu2000k (double jd_high, double jd_low,    double *dpsi, double *deps);  // for nutation_angles()




////////////////////////////////////////////////////////////////////////////////
////
//// SMC calculation functions
////

double GetGst(double dJD)
{
	double dJD_high, dJD_low, dGst;
	dJD_low = modf(dJD, &dJD_high);
	sidereal_time(dJD_high, dJD_low, 0.0, 1, 1, 0, &dGst);
	return dGst;
}


double GetJd(smctime_t ut)
{
    double dJD;
    //dJD = julian_date(ut->year, ut->month, ut->day, (double)ut->hour + (double)ut->min/60.0 + ut->sec/3600.0 );
    dJD = julian_date(ut.year, ut.month, ut.day, (double)ut.hour + (double)ut.min/60.0 + ut.sec/3600.0 );
	return dJD;
}


double GetAltitude(double HA, double Dec, double Latitude) // HA: hour,  Dec&Latitude: degree
{
	const double DegToRad = 0.017453292519943296;
	const double RadToDeg = 57.295779513082321;
    
	double cosz;
	cosz  = sin(Latitude*DegToRad)*sin(Dec*DegToRad)
			+ cos(Latitude*DegToRad)*cos(Dec*DegToRad)*cos(HA*15.0*DegToRad);

	return ( 90.0 - acos(cosz)*RadToDeg );	// deg
}


double GetAzimuth (double HA, double Dec, double Latitude) // HA: hour,  Dec&Latitude: degree
{
	const double DegToRad = 0.017453292519943296;
	const double RadToDeg = 57.295779513082321;

	double cosz, altitude, azimuth, cosA;

	if( HA<0.0 ) HA += 24.0;
	if( HA>=24.0 ) HA -= 24.0;

	cosz  = sin(Latitude*DegToRad)*sin(Dec*DegToRad) 
			+ cos(Latitude*DegToRad)*cos(Dec*DegToRad)*cos(HA*15.0*DegToRad);

	altitude = 90.0 - acos(cosz)*RadToDeg;	// Deg

	if((fabs(altitude)< 0.000001) && (fabs(altitude)>-0.000001)) altitude = 0.000001;
	if( fabs(altitude)> 89.999999 ) altitude =  89.999999;
	if( fabs(altitude)<-89.999999 ) altitude = -89.999999;

	cosA = sin(Dec*DegToRad)/( cos(Latitude*DegToRad)*sin( (90-altitude)*DegToRad ) )
				- tan(Latitude*DegToRad)/tan( (90.0-altitude)*DegToRad );
	if(fabs(cosA)>1.0) cosA = -1.0;

	azimuth = acos(cosA) * RadToDeg;

	if( HA>=0.0 && HA<12.0 ) azimuth = 360.0-azimuth;

	return azimuth;
}


double GetAirmass(double HA, double Dec, double Latitude)	// HA: hour,  Dec&Latitude: degree
{
	const double DegToRad = 0.017453292519943296;
	//const double RadToDeg = 57.295779513082321;

    double secz;
	secz  = 1.0 / (							// airmass±¸ÇÏ±â ( z == secz )
		sin(Latitude*DegToRad)*sin(Dec*DegToRad)
		+ cos(Latitude*DegToRad)*cos(Dec*DegToRad)*cos(HA*15.0*DegToRad)
		);

    return ( secz - 0.0018167*(secz-1.0) - 0.002875*pow((secz-1.0),2.0) - 0.00008083*pow((secz-1.0),3.0) );
}


void GetAltAzmAir(double HA, double Dec, double Latitude, double *Alt, double *Azm, double *Airmass) // HA: hour,  Dec,Latitude,Alt,Azm: degree
{
	const double DegToRad = 0.017453292519943296;
	const double RadToDeg = 57.295779513082321;

	double altitude, azimuth, airmass, cosz, cosA, secz;

	if( HA<0.0 ) HA += 24.0;
	if( HA>=24.0 ) HA -= 24.0;

	cosz  = sin(Latitude*DegToRad)*sin(Dec*DegToRad) 
			+ cos(Latitude*DegToRad)*cos(Dec*DegToRad)*cos(HA*15.0*DegToRad);
	secz  = 1.0/cosz;
	
	altitude = 90.0 - acos(cosz)*RadToDeg;	// Deg
	airmass  = secz - 0.0018167*(secz-1.0) - 0.002875*pow((secz-1.0),2.0) - 0.00008083*pow((secz-1.0),3.0);

	if((fabs(altitude)< 0.000001) && (fabs(altitude)>-0.000001)) altitude = 0.000001;
	if( fabs(altitude)> 89.999999 ) altitude =  89.999999;
	if( fabs(altitude)<-89.999999 ) altitude = -89.999999;

	cosA = sin(Dec*DegToRad)/( cos(Latitude*DegToRad)*sin( (90-altitude)*DegToRad ) )
				- tan(Latitude*DegToRad)/tan( (90.0-altitude)*DegToRad );
	if(fabs(cosA)>1.0) cosA = -1.0;

	azimuth = acos(cosA) * RadToDeg;

	if( HA>=0.0 && HA<12.0 ) azimuth = 360.0-azimuth;

	*Alt     = altitude;
	*Azm     = azimuth;
	*Airmass = airmass;
}


void SetSmctime(struct tm tmtime, smctime_t *psmctime)
{
  psmctime->year = tmtime.tm_year + 1900;
  psmctime->month = tmtime.tm_mon + 1;
  psmctime->day = tmtime.tm_mday;
  psmctime->hour = tmtime.tm_hour;
  psmctime->min = tmtime.tm_min;
  psmctime->sec = (double)tmtime.tm_sec;
  psmctime->secse = (UINT)mktime(&tmtime);
}

//------------------------------------------------------------------------------
// trans1060() - convert decimal to sexagesimal system and return the sign
//  - lastly modified at TCSAgent v1.6.4
//  * NOTE
//    nDP should be matched to rounding-off format in printf().
//    For examples, "%02.0f" --> nDP=0 / "%04.1f" --> nDP=1 / "%06.3f" --> nDP=3
//    Don't use only rounding-off format in printf() such as %02.0f, %05.2f, ..
//    to round dSec off to some decimal places to avoid 60.0 error of sec field.
//    nDP should be less than 10. (0 <= nDP <= 10)

char trans1060(double dHour, int *pnHour, int *pnMin, double *pdSec, int nDP)
{
  char cSign;
  double dMin, dRDT;

  if(nDP<0) nDP=0;
  dRDT = pow10(nDP);  // Rounding-down term, added at v1.6.4
  dRDT = pow(10.0, (double)nDP);  // For Windows version

  if(dHour<0.0) {cSign = '-';dHour*=-1.0;}
  else          {cSign = '+';           ;}

  dHour += 0.0000000006/3600;  // tunned in modification for v1.6.4.3
  //// a trick for debugging and a tunning term for precise conversion
  //// This value should be between ~0.00000000003/3600(1E-14) and 0.001/3600.

  *pnHour = (int)dHour;    dMin = ( dHour - (double)*pnHour ) * 60.0;
  *pnMin  = (int)dMin ;  *pdSec = ( dMin  - (double)*pnMin  ) * 60.0;

  *pdSec = fabs ( *pdSec );
  *pdSec = floor( *pdSec * dRDT ) / dRDT;

  return cSign;
}
//// For more improvement, a integer type millisecond could be used instead of rounding-down float type..


////////////////////////////////////////////////////////////////////////////////
////
//// Functions for sidereal_time() & julian_date(), from novas.c
////

/*
  Naval Observatory Vector Astrometry Software (NOVAS)
  C Edition, Version 3.1

  novas.c: Main library

  U. S. Naval Observatory
  Astronomical Applications Dept.
  Washington, DC
  http://www.usno.navy.mil/USNO/astronomical-applications
*/

////#ifndef _NOVAS_
////   #include "novas.h"
////#endif

#include <math.h>

/*
   Global variables.

   'PSI_COR' and 'EPS_COR' are celestial pole offsets for high-
   precision applications.  See function 'cel_pole' for more details.
*/

static double PSI_COR = 0.0;
static double EPS_COR = 0.0;


/********sidereal_time */

short int sidereal_time (double jd_high, double jd_low,
                         double delta_t,short int gst_type,
                         short int method, short int accuracy,

                         double *gst)
/*
------------------------------------------------------------------------

   PURPOSE:
      Computes the Greenwich sidereal time, either mean or apparent, at
      Julian date 'jd_high' + 'jd_low'.

   REFERENCES:
      Kaplan, G. (2005), US Naval Observatory Circular 179.

   INPUT
   ARGUMENTS:
      jd_high (double)
         High-order part of UT1 Julian date.
      jd_low (double)
         Low-order part of UT1 Julian date.
      delta_t (double)
         Difference TT-UT1 at 'jd_high'+'jd_low', in seconds
         of time.
      gst_type (short int)
         = 0 ... compute Greenwich mean sidereal time
         = 1 ... compute Greenwich apparent sidereal time
      method (short int)
         Selection for method
            = 0 ... CIO-based method
            = 1 ... equinox-based method
      accuracy (short int)
         Selection for accuracy
            = 0 ... full accuracy
            = 1 ... reduced accuracy

   OUTPUT
   ARGUMENTS:
      *gst (double)
         Greenwich (mean or apparent) sidereal time, in hours.

   RETURNED
   VALUE:
      (short int)
         = 0         ... everything OK
         = 1         ... invalid value of 'accuracy'
         = 2         ... invalid value of 'method'
         > 10, < 30  ... 10 + error from function 'cio_rai'

   GLOBALS
   USED:
      T0, RAD2DEG        novascon.c

   FUNCTIONS
   CALLED:
      tdb2tt             novas.c
      era                novas.c
      e_tilt             novas.c
      cio_location       novas.c
      cio_basis          novas.c
      nutation           novas.c
      precession         novas.c
      frame_tie          novas.c
      fabs               math.h
      atan2              math.h
      fmod               math.h

   VER./DATE/
   PROGRAMMER:
      V1.0/06-92/TKB (USNO/NRL Optical Interfer.) Translate Fortran.
      V1.1/08-93/WTH (USNO/AA) Update to C programing standards.
      V1.2/03-98/JAB (USNO/AA) Expand documentation.
      V1.3/08-98/JAB (USNO/AA) Match flow of the Fortran counterpart.
      V2.0/09-03/JAB (USNO/AA) Incorporate the 2nd-reference changes.
      V2.1/08-04/JAB (USNO/AA) Incorporate the 1st-reference changes.
      V2.2/12-05/WKP (USNO/AA) Updated error handling.
      V2.3/01-06/WKP (USNO/AA) Changed 'mode' to 'method' and 'accuracy'.
      V2.4/04-06/JAB (USNO/AA) Use precession-in-RA terms in mean
                               sidereal time from third reference.
      V2.5/07-06/JAB (USNO/AA) Implement 'cio_location' construct.
      V2.6/06-08/WKP (USNO/AA) Changed value of direction argument in
                               call to 'nutation' from 1 to -1 for
                               consistency.
      V2.7/03-11/WKP (USNO/AA) Updated prolog description to clarify
                               this function computes either mean or
                               apparent sidereal time, and removed
                               Note 1 for consistency with Fortran.

   NOTES:
      1. The Julian date may be split at any point, but for highest
      precision, set 'jd_high' to be the integral part of the Julian
      date, and set 'jd_low' to be the fractional part.
      2. This function is the C version of NOVAS Fortran routine
      'sidtim'.

------------------------------------------------------------------------
*/
{
   short int error = 0;
   short int ref_sys;

   static double ee;
   static double jd_last = -99.0;
   double unitx[3] = {1.0, 0.0, 0.0};
   double jd_ut, jd_tt, jd_tdb, tt_temp, t, theta, a, b, c, d,
      ra_cio, x[3], y[3], z[3], w1[3], w2[3], eq[3], ha_eq, st,
      secdiff, eqeq;

/*
   Invalid value of 'accuracy'.
*/

   if ((accuracy < 0) || (accuracy > 1))
      return (error = 1);

/*
   Time argument for precession and nutation components of sidereal
   time is TDB.  First approximation is TDB = TT, then refine.
*/

   jd_ut = jd_high + jd_low;
   jd_tt = jd_ut + (delta_t / 86400.0);
   jd_tdb = jd_tt;
   tdb2tt (jd_tdb, &tt_temp,&secdiff);
   jd_tdb = jd_tt + (secdiff / 86400.0);

   t = (jd_tdb - T0) / 36525.0;

/*
   Compute the Earth Rotation Angle.  Time argument is UT1.
*/

   theta = era (jd_high, jd_low);

/*
   Compute the equation of the equinoxes if needed, depending upon the
   input values of 'gst_type' and 'method'.  If not needed, set to zero.
*/

   if (((gst_type == 0) && (method == 0)) ||       /* GMST; CIO-TIO */
       ((gst_type == 1) && (method == 1)))         /* GAST; equinox */
   {
      if (fabs (jd_tdb - jd_last) > 1.0e-8)
      {
         e_tilt (jd_tdb,accuracy, &a,&b,&ee,&c,&d);
         jd_last = jd_tdb;
      }
      eqeq = ee * 15.0;
   }
    else
   {
      eqeq = 0.0;
   }

/*
   Compute Greenwich sidereal time depending upon input values of
   'method' and 'gst_type'.
*/

   switch (method)
   {
      case (0):

/*
   Use 'CIO-TIO-theta' method.  See Circular 179, Section 6.5.4.
*/

/*
   Obtain the basis vectors, in the GCRS, of the celestial intermediate
   system.
*/

         if ((error = cio_location (jd_tdb,accuracy, &ra_cio,
            &ref_sys)) != 0)
         {
            *gst = 99.0;
            return (error += 10);
         }

         cio_basis (jd_tdb,ra_cio,ref_sys,accuracy, x,y,z);

/*
   Compute the direction of the true equinox in the GCRS.
*/

         nutation (jd_tdb,-1,accuracy,unitx, w1);
         precession (jd_tdb,w1,T0, w2);
         frame_tie (w2,-1, eq);

/*
   Compute the hour angle of the equinox wrt the TIO meridian
   (near Greenwich, but passes through the CIP and TIO).
*/

         ha_eq = theta - atan2 ((eq[0] * y[0] + eq[1] * y[1] +
            eq[2] * y[2]), (eq[0] * x[0] + eq[1] * x[1] +
            eq[2] * x[2])) * RAD2DEG;

/*
   For mean sidereal time, subtract the equation of the equinoxes.
*/

         ha_eq -= (eqeq / 240.0);

         ha_eq = fmod (ha_eq, 360.0) / 15.0;
         if (ha_eq < 0.0)
            ha_eq += 24.0;
         *gst = ha_eq;
         break;

      case (1):

/*
   Use equinox method.  See Circular 179, Section 2.6.2.
*/

/*
   Precession-in-RA terms in mean sidereal time taken from third
   reference, eq. (42), with coefficients in arcseconds.
*/

         st = eqeq + 0.014506 +
               (((( -    0.0000000368   * t
                    -    0.000029956  ) * t
                    -    0.00000044   ) * t
                    +    1.3915817    ) * t
                    + 4612.156534     ) * t;

/*
   Form the Greenwich sidereal time.
*/

         *gst = fmod ((st / 3600.0 + theta), 360.0) / 15.0;

         if (*gst < 0.0)
            *gst += 24.0;
         break;

/*
   Invalid value of 'method'.
*/

      default:
         *gst = 99.0;
         error = 2;
         break;
   }

   return (error);
}

/********era */

double era (double jd_high, double jd_low)
/*
------------------------------------------------------------------------

   PURPOSE:
      This function returns the value of the Earth Rotation Angle
      (theta) for a given UT1 Julian date.  The expression used is
      taken from the note to IAU Resolution B1.8 of 2000.

   REFERENCES:
      IAU Resolution B1.8, adopted at the 2000 IAU General Assembly,
         Manchester, UK.
      Kaplan, G. (2005), US Naval Observatory Circular 179.

   INPUT
   ARGUMENTS:
      jd_high (double)
         High-order part of UT1 Julian date.
      jd_low (double)
         Low-order part of UT1 Julian date.

   OUTPUT
   ARGUMENTS:
      None.

   RETURNED
   VALUE:
      (double)
         The Earth Rotation Angle (theta) in degrees.

   GLOBALS
   USED:
      T0                 novascon.c

   FUNCTIONS
   CALLED:
      fmod               math.h

   VER./DATE/
   PROGRAMMER:
      V1.0/09-03/JAB (USNO/AA)

   NOTES:
      1. The algorithm used here is equivalent to the canonical
      theta = 0.7790572732640 + 1.00273781191135448 * t,
      where t is the time in days from J2000 (t = jd_high +
      jd_low - T0), but it avoids many two-PI 'wraps' that decrease
      precision (adopted from SOFA Fortran routine iau_era00; see
      also expression at top of page 35 of IERS Conventions (1996)).
      2. This function is the C version of NOVAS Fortran routine
      'erot'.

------------------------------------------------------------------------
*/

{
   double theta, thet1, thet2, thet3;

   thet1 = 0.7790572732640 + 0.00273781191135448 * (jd_high - T0);
   thet2 = 0.00273781191135448 * jd_low;
   thet3 = fmod (jd_high, 1.0) + fmod (jd_low, 1.0);

   theta = fmod (thet1 + thet2 + thet3, 1.0) * 360.0;
   if (theta < 0.0)
      theta += 360.0;

   return theta;
}

/********e_tilt */

void e_tilt (double jd_tdb, short int accuracy,

             double *mobl, double *tobl, double *ee, double *dpsi,
             double *deps)
/*
------------------------------------------------------------------------

   PURPOSE:
      Computes quantities related to the orientation of the Earth's
      rotation axis at Julian date 'jd_tdb'.

   REFERENCES:
      None.

   INPUT
   ARGUMENTS:
      jd_tdb (double)
         TDB Julian Date.
      accuracy (short int)
         Selection for accuracy
            = 0 ... full accuracy
            = 1 ... reduced accuracy

   OUTPUT
   ARGUMENTS:
      *mobl (double)
         Mean obliquity of the ecliptic in degrees at 'jd_tdb'.
      *tobl (double)
         True obliquity of the ecliptic in degrees at 'jd_tdb'.
      *ee (double)
         Equation of the equinoxes in seconds of time at 'jd_tdb'.
      *dpsi (double)
         Nutation in longitude in arcseconds at 'jd_tdb'.
      *deps (double)
         Nutation in obliquity in arcseconds at 'jd_tdb'.

   RETURNED
   VALUE:
      None.

   GLOBALS
   USED:
      PSI_COR, EPS_COR   novas.c
      T0, ASEC2RAD       novascon.c
      DEG2RAD            novascon.c

   FUNCTIONS
   CALLED:
      nutation_angles    novas.c
      ee_ct              novas.c
      mean_obliq         novas.c
      fabs               math.h
      cos                math.h

   VER./DATE/
   PROGRAMMER:
      V1.0/08-93/WTH (USNO/AA) Translate Fortran.
      V1.1/06-97/JAB (USNO/AA) Incorporate IAU (1994) and IERS (1996)
                               adjustment to the "equation of the
                               equinoxes".
      V1.2/10-97/JAB (USNO/AA) Implement function that computes
                               arguments of the nutation series.
      V1.3/07-98/JAB (USNO/AA) Use global variables 'PSI_COR' and
                               'EPS_COR' to apply celestial pole offsets
                               for high-precision applications.
      V2.0/10-03/JAB (USNO/AA) Update function for IAU 2000 resolutions.
      V2.1/12-04/JAB (USNO/AA) Add 'mode' argument.
      V2.2/01-06/WKP (USNO/AA) Changed 'mode' to 'accuracy'.

   NOTES:
      1. Values of the celestial pole offsets 'PSI_COR' and 'EPS_COR'
      are set using function 'cel_pole', if desired.  See the prolog
      of 'cel_pole' for details.
      2. This function is the C version of NOVAS Fortran routine
      'etilt'.

------------------------------------------------------------------------
*/
{
   static short int accuracy_last = 0;
   short int acc_diff;

   static double jd_last = 0.0;
   static double dp, de, c_terms;
   double t, d_psi, d_eps, mean_ob, true_ob, eq_eq;

/*
   Compute time in Julian centuries from epoch J2000.0.
*/

   t = (jd_tdb - T0) / 36525.0;

/*
   Check for difference in accuracy mode from last call.
*/

   acc_diff = accuracy - accuracy_last;

/*
   Compute the nutation angles (arcseconds) if the input Julian date
   is significantly different from the last Julian date, or the
   accuracy mode has changed from the last call.
*/

   if (((fabs (jd_tdb - jd_last)) > 1.0e-8) || (acc_diff != 0))
   {
      nutation_angles (t,accuracy, &dp,&de);

/*
   Obtain complementary terms for equation of the equinoxes in
   arcseconds.
*/

      c_terms = ee_ct (jd_tdb,0.0,accuracy) / ASEC2RAD;

/*
   Reset the values of the last Julian date and last mode.
*/

      jd_last = jd_tdb;
      accuracy_last = accuracy;
   }

/*
   Apply observed celestial pole offsets.
*/

   d_psi = dp + PSI_COR;
   d_eps = de + EPS_COR;

/*
   Compute mean obliquity of the ecliptic in arcseconds.
*/

   mean_ob = mean_obliq (jd_tdb);

/*
   Compute true obliquity of the ecliptic in arcseconds.
*/

   true_ob = mean_ob + d_eps;

/*
   Convert obliquity values to degrees.
*/

   mean_ob /= 3600.0;
   true_ob /= 3600.0;

/*
   Compute equation of the equinoxes in seconds of time.
*/

   eq_eq = d_psi * cos (mean_ob * DEG2RAD) + c_terms;
   eq_eq /= 15.0;

/*
   Set output values.
*/

   *dpsi = d_psi;
   *deps = d_eps;
   *ee   = eq_eq;
   *mobl = mean_ob;
   *tobl = true_ob;

   return;
}

/********ee_ct */

double ee_ct (double jd_high, double jd_low, short int accuracy)
/*
------------------------------------------------------------------------

   PURPOSE:
      To compute the "complementary terms" of the equation of the
      equinoxes.

   REFERENCES:
      Capitaine, N., Wallace, P.T., and McCarthy, D.D. (2003). Astron. &
         Astrophys. 406, p. 1135-1149. Table 3.
      IERS Conventions (2010), Chapter 5, p. 60, Table 5.2e.
         (Table 5.2e presented in the printed publication is a truncated
         series. The full series, which is used in NOVAS, is available
         on the IERS Conventions Center website in file tab5.2e.txt.)
         ftp://tai.bipm.org/iers/conv2010/chapter5/

   INPUT
   ARGUMENTS:
      jd_high (double)
         High-order part of TT Julian date.
      jd_low (double)
         Low-order part of TT Julian date.
      accuracy (short int)
         Selection for accuracy
            = 0 ... full accuracy
            = 1 ... reduced accuracy

   OUTPUT
   ARGUMENTS:
      None

   RETURNED
   VALUE:
      (double)
         Complementary terms, in radians.

   GLOBALS
   USED:
      T0, ASEC2RAD       novascon.c
      TWOPI              novascon.c

   FUNCTIONS
   CALLED:
      norm_ang           novas.c
      fund_args          novas.c
      fmod               math.h
      sin                math.h
      cos                math.h

   VER./DATE/
   PROGRAMMER:
      V1.0/09-03/JAB (USNO/AA)
      V1.1/12-04/JAB (USNO/AA) Added low-accuracy formula.
      V1.2/01-06/WKP (USNO/AA) Changed 'mode' to 'accuracy'.
      V1.3/11-10/JAB (USNO/AA) Updated reference and notes.
      V1.4/03-11/WKP (USNO/AA) Added braces to 2-D array initialization
                               to quiet gcc warnings.

   NOTES:
      1. The series used in this function was derived from the first
      reference.  This same series was also adopted for use in the IAU's
      Standards of Fundamental Astronomy (SOFA) software (i.e.,
      subroutine eect00.for and function eect00.c).
      2. The low-accuracy series used in this function is a simple
      implementation derived from the first reference, in which terms
      smaller than 2 microarcseconds have been omitted.
      3. This function is based on NOVAS Fortran routine 'eect2000',
      with the low-accuracy formula taken from NOVAS Fortran routine
      'etilt'.

------------------------------------------------------------------------
*/
{
   short int i, j;

   double t, fa[14], fa2[5], s0, s1, a, c_terms;

/*
   Argument coefficients for t^0.
*/

   const short int ke0_t[33][14] = {
      {0,  0,  0,  0,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0},
      {0,  0,  0,  0,  2,  0,  0,  0,  0,  0,  0,  0,  0,  0},
      {0,  0,  2, -2,  3,  0,  0,  0,  0,  0,  0,  0,  0,  0},
      {0,  0,  2, -2,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0},
      {0,  0,  2, -2,  2,  0,  0,  0,  0,  0,  0,  0,  0,  0},
      {0,  0,  2,  0,  3,  0,  0,  0,  0,  0,  0,  0,  0,  0},
      {0,  0,  2,  0,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0},
      {0,  0,  0,  0,  3,  0,  0,  0,  0,  0,  0,  0,  0,  0},
      {0,  1,  0,  0,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0},
      {0,  1,  0,  0, -1,  0,  0,  0,  0,  0,  0,  0,  0,  0},
      {1,  0,  0,  0, -1,  0,  0,  0,  0,  0,  0,  0,  0,  0},
      {1,  0,  0,  0,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0},
      {0,  1,  2, -2,  3,  0,  0,  0,  0,  0,  0,  0,  0,  0},
      {0,  1,  2, -2,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0},
      {0,  0,  4, -4,  4,  0,  0,  0,  0,  0,  0,  0,  0,  0},
      {0,  0,  1, -1,  1,  0, -8, 12,  0,  0,  0,  0,  0,  0},
      {0,  0,  2,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0},
      {0,  0,  2,  0,  2,  0,  0,  0,  0,  0,  0,  0,  0,  0},
      {1,  0,  2,  0,  3,  0,  0,  0,  0,  0,  0,  0,  0,  0},
      {1,  0,  2,  0,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0},
      {0,  0,  2, -2,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0},
      {0,  1, -2,  2, -3,  0,  0,  0,  0,  0,  0,  0,  0,  0},
      {0,  1, -2,  2, -1,  0,  0,  0,  0,  0,  0,  0,  0,  0},
      {0,  0,  0,  0,  0,  0,  8,-13,  0,  0,  0,  0,  0, -1},
      {0,  0,  0,  2,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0},
      {2,  0, -2,  0, -1,  0,  0,  0,  0,  0,  0,  0,  0,  0},
      {1,  0,  0, -2,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0},
      {0,  1,  2, -2,  2,  0,  0,  0,  0,  0,  0,  0,  0,  0},
      {1,  0,  0, -2, -1,  0,  0,  0,  0,  0,  0,  0,  0,  0},
      {0,  0,  4, -2,  4,  0,  0,  0,  0,  0,  0,  0,  0,  0},
      {0,  0,  2, -2,  4,  0,  0,  0,  0,  0,  0,  0,  0,  0},
      {1,  0, -2,  0, -3,  0,  0,  0,  0,  0,  0,  0,  0,  0},
      {1,  0, -2,  0, -1,  0,  0,  0,  0,  0,  0,  0,  0,  0}};

/*
   Argument coefficients for t^1.
*/

   const short int ke1[14] =
      {0,  0,  0,  0,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0};

/*
   Sine and cosine coefficients for t^0.
*/

   const double se0_t[33][2] = {
      {+2640.96e-6,          -0.39e-6},
      {  +63.52e-6,          -0.02e-6},
      {  +11.75e-6,          +0.01e-6},
      {  +11.21e-6,          +0.01e-6},
      {   -4.55e-6,          +0.00e-6},
      {   +2.02e-6,          +0.00e-6},
      {   +1.98e-6,          +0.00e-6},
      {   -1.72e-6,          +0.00e-6},
      {   -1.41e-6,          -0.01e-6},
      {   -1.26e-6,          -0.01e-6},
      {   -0.63e-6,          +0.00e-6},
      {   -0.63e-6,          +0.00e-6},
      {   +0.46e-6,          +0.00e-6},
      {   +0.45e-6,          +0.00e-6},
      {   +0.36e-6,          +0.00e-6},
      {   -0.24e-6,          -0.12e-6},
      {   +0.32e-6,          +0.00e-6},
      {   +0.28e-6,          +0.00e-6},
      {   +0.27e-6,          +0.00e-6},
      {   +0.26e-6,          +0.00e-6},
      {   -0.21e-6,          +0.00e-6},
      {   +0.19e-6,          +0.00e-6},
      {   +0.18e-6,          +0.00e-6},
      {   -0.10e-6,          +0.05e-6},
      {   +0.15e-6,          +0.00e-6},
      {   -0.14e-6,          +0.00e-6},
      {   +0.14e-6,          +0.00e-6},
      {   -0.14e-6,          +0.00e-6},
      {   +0.14e-6,          +0.00e-6},
      {   +0.13e-6,          +0.00e-6},
      {   -0.11e-6,          +0.00e-6},
      {   +0.11e-6,          +0.00e-6},
      {   +0.11e-6,          +0.00e-6}};
/*
   Sine and cosine coefficients for t^1.
*/

   const double se1[2] =
      {   -0.87e-6,          +0.00e-6};

/*
   Interval between fundamental epoch J2000.0 and current date.
*/

      t = ((jd_high - T0) + jd_low) / 36525.0;

/*
   High accuracy mode.
*/

   if (accuracy == 0)
   {

/*
   Fundamental Arguments.

   Mean Anomaly of the Moon.
*/

      fa[0] = norm_ang ((485868.249036 +
                         (715923.2178 +
                         (    31.8792 +
                         (     0.051635 +
                         (    -0.00024470)
                         * t) * t) * t) * t) * ASEC2RAD
                         + fmod (1325.0*t, 1.0) * TWOPI);

/*
   Mean Anomaly of the Sun.
*/

      fa[1] = norm_ang ((1287104.793048 +
                         (1292581.0481 +
                         (     -0.5532 +
                         (     +0.000136 +
                         (     -0.00001149)
                         * t) * t) * t) * t) * ASEC2RAD
                         + fmod (99.0*t, 1.0) * TWOPI);

/*
   Mean Longitude of the Moon minus Mean Longitude of the Ascending
   Node of the Moon.
*/

      fa[2] = norm_ang (( 335779.526232 +
                         ( 295262.8478 +
                         (    -12.7512 +
                         (     -0.001037 +
                         (      0.00000417)
                         * t) * t) * t) * t) * ASEC2RAD
                         + fmod (1342.0*t, 1.0) * TWOPI);

/*
   Mean Elongation of the Moon from the Sun.
*/

      fa[3] = norm_ang ((1072260.703692 +
                         (1105601.2090 +
                         (     -6.3706 +
                         (      0.006593 +
                         (     -0.00003169)
                         * t) * t) * t) * t) * ASEC2RAD
                         + fmod (1236.0*t, 1.0) * TWOPI);

/*
   Mean Longitude of the Ascending Node of the Moon.
*/

      fa[4] = norm_ang (( 450160.398036 +
                         (-482890.5431 +
                         (      7.4722 +
                         (      0.007702 +
                         (     -0.00005939)
                         * t) * t) * t) * t) * ASEC2RAD
                         + fmod (-5.0*t, 1.0) * TWOPI);

      fa[ 5] = norm_ang (4.402608842 + 2608.7903141574 * t);
      fa[ 6] = norm_ang (3.176146697 + 1021.3285546211 * t);
      fa[ 7] = norm_ang (1.753470314 +  628.3075849991 * t);
      fa[ 8] = norm_ang (6.203480913 +  334.0612426700 * t);
      fa[ 9] = norm_ang (0.599546497 +   52.9690962641 * t);
      fa[10] = norm_ang (0.874016757 +   21.3299104960 * t);
      fa[11] = norm_ang (5.481293872 +    7.4781598567 * t);
      fa[12] = norm_ang (5.311886287 +    3.8133035638 * t);
      fa[13] =          (0.024381750 +    0.00000538691 * t) * t;

/*
   Evaluate the complementary terms.
*/

      s0 = 0.0;
      s1 = 0.0;

      for (i = 32; i >= 0; i--)
      {
         a = 0.0;

         for (j = 0; j < 14; j++)
         {
            a += (double) ke0_t[i][j] * fa[j];
         }

         s0 += (se0_t[i][0] * sin (a) + se0_t[i][1] * cos (a));
      }

      a = 0.0;

      for (j = 0; j < 14; j++)
      {
         a += (double) (ke1[j]) * fa[j];
      }

      s1 += (se1[0] * sin (a) + se1[1] * cos (a));

      c_terms = (s0 + s1 * t);
   }

    else

/*
   Low accuracy mode: Terms smaller than 2 microarcseconds omitted.
*/

   {
      fund_args (t, fa2);
      c_terms =
          2640.96e-6 * sin (fa2[4])
         +  63.52e-6 * sin (2.0 * fa2[4])
         +  11.75e-6 * sin (2.0 * fa2[2] - 2.0 * fa2[3] + 3.0 * fa2[4])
         +  11.21e-6 * sin (2.0 * fa2[2] - 2.0 * fa2[3] +       fa2[4])
         -   4.55e-6 * sin (2.0 * fa2[2] - 2.0 * fa2[3] + 2.0 * fa2[4])
         +   2.02e-6 * sin (2.0 * fa2[2]                + 3.0 * fa2[4])
         +   1.98e-6 * sin (2.0 * fa2[2]                +       fa2[4])
         -   1.72e-6 * sin (3.0 * fa2[4])
         -   0.87e-6 * t * sin (fa2[4]);
   }

   return (c_terms *= ASEC2RAD);
}

/********frame_tie */

void frame_tie (double *pos1, short int direction,

                double *pos2)
/*
------------------------------------------------------------------------

   PURPOSE:
      To transform a vector from the dynamical reference system to the
      International Celestial Reference System (ICRS), or vice versa.
      The dynamical reference system is based on the dynamical mean
      equator and equinox of J2000.0.  The ICRS is based on the space-
      fixed ICRS axes defined by the radio catalog positions of several
      hundred extragalactic objects.

   REFERENCES:
      Hilton, J. and Hohenkerk, C. (2004), Astronomy and Astrophysics
         413, 765-770, eq. (6) and (8).
      IERS (2003) Conventions, Chapter 5.

   INPUT
   ARGUMENTS:
      pos1[3] (double)
         Position vector, equatorial rectangular coordinates.
      direction (short int)
         Set 'direction' < 0 for dynamical to ICRS transformation.
         Set 'direction' >= 0 for ICRS to dynamical transformation.

   OUTPUT
   ARGUMENTS:
      pos2[3] (double)
         Position vector, equatorial rectangular coordinates.

   RETURNED
   VALUE:
      None.

   GLOBALS
   USED:
      ASEC2RAD           novascon.c

   FUNCTIONS
   CALLED:
      None.

   VER./DATE/
   PROGRAMMER:
      V1.0/09-03/JAB (USNO/AA)
      V1.1/02-06/WKP (USNO/AA) Added second-order corrections to diagonal
                               elements.

   NOTES:
      1. For geocentric coordinates, the same transformation is used
      between the dynamical reference system and the GCRS.
      2. This function is the C version of NOVAS Fortran routine 'frame'.

------------------------------------------------------------------------
*/
{
   static short int compute_matrix = 1;

/*
   'xi0', 'eta0', and 'da0' are ICRS frame biases in arcseconds taken
   from IERS (2003) Conventions, Chapter 5.
*/

   const double xi0  = -0.0166170;
   const double eta0 = -0.0068192;
   const double da0  = -0.01460;
   static double xx, yx, zx, xy, yy, zy, xz, yz, zz;

/*
   Compute elements of rotation matrix to first order the first time
   this function is called.  Elements will be saved for future use and
   not recomputed.
*/

   if (compute_matrix == 1)
   {
      xx =  1.0;
      yx = -da0  * ASEC2RAD;
      zx =  xi0  * ASEC2RAD;
      xy =  da0  * ASEC2RAD;
      yy =  1.0;
      zy =  eta0 * ASEC2RAD;
      xz = -xi0  * ASEC2RAD;
      yz = -eta0 * ASEC2RAD;
      zz =  1.0;

/*
   Include second-order corrections to diagonal elements.
*/

      xx = 1.0 - 0.5 * (yx * yx + zx * zx);
      yy = 1.0 - 0.5 * (yx * yx + zy * zy);
      zz = 1.0 - 0.5 * (zy * zy + zx * zx);

      compute_matrix = 0;
   }

/*
   Perform the rotation in the sense specified by 'direction'.
*/

   if (direction < 0)
   {

/*
   Perform rotation from dynamical system to ICRS.
*/

      pos2[0] = xx * pos1[0] + yx * pos1[1] + zx * pos1[2];
      pos2[1] = xy * pos1[0] + yy * pos1[1] + zy * pos1[2];
      pos2[2] = xz * pos1[0] + yz * pos1[1] + zz * pos1[2];
   }
    else
   {

/*
   Perform rotation from ICRS to dynamical system.
*/

      pos2[0] = xx * pos1[0] + xy * pos1[1] + xz * pos1[2];
      pos2[1] = yx * pos1[0] + yy * pos1[1] + yz * pos1[2];
      pos2[2] = zx * pos1[0] + zy * pos1[1] + zz * pos1[2];
   }

   return;
}

/********precession */

short int precession (double jd_tdb1, double *pos1, double jd_tdb2,

                      double *pos2)
/*
------------------------------------------------------------------------

   PURPOSE:
      Precesses equatorial rectangular coordinates from one epoch to
      another.  One of the two epochs must be J2000.0.  The coordinates
      are referred to the mean dynamical equator and equinox of the two
      respective epochs.

   REFERENCES:
      Explanatory Supplement To The Astronomical Almanac, pp. 103-104.
      Capitaine, N. et al. (2003), Astronomy And Astrophysics 412,
         pp. 567-586.
      Hilton, J. L. et al. (2006), IAU WG report, Celest. Mech., 94,
         pp. 351-367.

   INPUT
   ARGUMENTS:
      jd_tdb1 (double)
         TDB Julian date of first epoch.  See Note 1 below.
      pos1[3] (double)
         Position vector, geocentric equatorial rectangular coordinates,
         referred to mean dynamical equator and equinox of first epoch.
      jd_tdb2 (double)
         TDB Julian date of second epoch.  See Note 1 below.

   OUTPUT
   ARGUMENTS:
      pos2[3] (double)
         Position vector, geocentric equatorial rectangular coordinates,
         referred to mean dynamical equator and equinox of second epoch.

   RETURNED
   VALUE:
      (short int)
         = 0 ... everything OK.
         = 1 ... Precession not to or from J2000.0; 'jd_tdb1' or 'jd_tdb2'
                 not 2451545.0.

   GLOBALS
   USED:
      T0, ASEC2RAD       novascon.c

   FUNCTIONS
   CALLED:
      fabs               math.h
      sin                math.h
      cos                math.h

   VER./DATE/
   PROGRAMMER:
      V1.0/01-93/TKB (USNO/NRL Optical Interfer.) Translate Fortran.
      V1.1/08-93/WTH (USNO/AA) Update to C Standards.
      V1.2/03-98/JAB (USNO/AA) Change function type from 'short int' to
                               'void'.
      V1.3/12-99/JAB (USNO/AA) Precompute trig terms for greater
                               efficiency.
      V2.0/10-03/JAB (USNO/AA) Update function for consistency with
                               IERS (2000) Conventions.
      V2.1/01-05/JAB (USNO/AA) Update expressions for the precession
                               angles (extra significant digits).
      V2.2/04-06/JAB (USNO/AA) Update model to 2006 IAU convention.
                               This is model "P03" of second reference.
      V2.3/03-10/JAB (USNO/AA) Implement 'first-time' to fix bug when
                                'jd_tdb2' is 'T0' on first call to
                                function.

   NOTES:
      1. Either 'jd_tdb1' or 'jd_tdb2' must be 2451545.0 (J2000.0) TDB.
      2. This function is the C version of NOVAS Fortran routine
      'preces'.

------------------------------------------------------------------------
*/
{
   static short int first_time = 1;
   short int error = 0;

   static double t_last = 0.0;
   static double xx, yx, zx, xy, yy, zy, xz, yz, zz;
   double eps0 = 84381.406;
   double  t, psia, omegaa, chia, sa, ca, sb, cb, sc, cc, sd, cd;

/*
   Check to be sure that either 'jd_tdb1' or 'jd_tdb2' is equal to T0.
*/

   if ((jd_tdb1 != T0) && (jd_tdb2 != T0))
      return (error = 1);

/*
   't' is time in TDB centuries between the two epochs.
*/

   t = (jd_tdb2 - jd_tdb1) / 36525.0;

   if (jd_tdb2 == T0)
      t = -t;

   if ((fabs (t - t_last) >= 1.0e-15) || (first_time == 1))
   {

/*
   Numerical coefficients of psi_a, omega_a, and chi_a, along with
   epsilon_0, the obliquity at J2000.0, are 4-angle formulation from
   Capitaine et al. (2003), eqs. (4), (37), & (39).
*/

      psia   = ((((-    0.0000000951  * t
                   +    0.000132851 ) * t
                   -    0.00114045  ) * t
                   -    1.0790069   ) * t
                   + 5038.481507    ) * t;

      omegaa = ((((+    0.0000003337  * t
                   -    0.000000467 ) * t
                   -    0.00772503  ) * t
                   +    0.0512623   ) * t
                   -    0.025754    ) * t + eps0;

      chia   = ((((-    0.0000000560  * t
                   +    0.000170663 ) * t
                   -    0.00121197  ) * t
                   -    2.3814292   ) * t
                   +   10.556403    ) * t;

      eps0 = eps0 * ASEC2RAD;
      psia = psia * ASEC2RAD;
      omegaa = omegaa * ASEC2RAD;
      chia = chia * ASEC2RAD;

      sa = sin (eps0);
      ca = cos (eps0);
      sb = sin (-psia);
      cb = cos (-psia);
      sc = sin (-omegaa);
      cc = cos (-omegaa);
      sd = sin (chia);
      cd = cos (chia);
/*
   Compute elements of precession rotation matrix equivalent to
   R3(chi_a) R1(-omega_a) R3(-psi_a) R1(epsilon_0).
*/

      xx =  cd * cb - sb * sd * cc;
      yx =  cd * sb * ca + sd * cc * cb * ca - sa * sd * sc;
      zx =  cd * sb * sa + sd * cc * cb * sa + ca * sd * sc;
      xy = -sd * cb - sb * cd * cc;
      yy = -sd * sb * ca + cd * cc * cb * ca - sa * cd * sc;
      zy = -sd * sb * sa + cd * cc * cb * sa + ca * cd * sc;
      xz =  sb * sc;
      yz = -sc * cb * ca - sa * cc;
      zz = -sc * cb * sa + cc * ca;

      t_last = t;
      first_time = 0;
   }

   if (jd_tdb2 == T0)
   {

/*
   Perform rotation from epoch to J2000.0.
*/
      pos2[0] = xx * pos1[0] + xy * pos1[1] + xz * pos1[2];
      pos2[1] = yx * pos1[0] + yy * pos1[1] + yz * pos1[2];
      pos2[2] = zx * pos1[0] + zy * pos1[1] + zz * pos1[2];
   }
    else
   {

/*
   Perform rotation from J2000.0 to epoch.
*/

      pos2[0] = xx * pos1[0] + yx * pos1[1] + zx * pos1[2];
      pos2[1] = xy * pos1[0] + yy * pos1[1] + zy * pos1[2];
      pos2[2] = xz * pos1[0] + yz * pos1[1] + zz * pos1[2];
   }

   return (error = 0);
}

/********nutation */

void nutation (double jd_tdb, short int direction, short int accuracy,
               double *pos,

               double *pos2)
/*
------------------------------------------------------------------------

   PURPOSE:
      Nutates equatorial rectangular coordinates from mean equator and
      equinox of epoch to true equator and equinox of epoch. Inverse
      transformation may be applied by setting flag 'direction'.

   REFERENCES:
      Explanatory Supplement To The Astronomical Almanac, pp. 114-115.

   INPUT
   ARGUMENTS:
      jd_tdb (double)
         TDB Julian date of epoch.
      direction (short int)
         Flag determining 'direction' of transformation;
            direction  = 0 transformation applied, mean to true.
            direction != 0 inverse transformation applied, true to mean.
      accuracy (short int)
         Selection for accuracy
            = 0 ... full accuracy
            = 1 ... reduced accuracy
      pos[3] (double)
         Position vector, geocentric equatorial rectangular coordinates,
         referred to mean equator and equinox of epoch.

   OUTPUT
   ARGUMENTS:
      pos2[3] (double)
         Position vector, geocentric equatorial rectangular coordinates,
         referred to true equator and equinox of epoch.

   RETURNED
   VALUE:
      None.

   GLOBALS
   USED:
      DEG2RAD, ASEC2RAD  novascon.c

   FUNCTIONS
   CALLED:
      e_tilt             novas.c
      cos                math.h
      sin                math.h

   VER./DATE/
   PROGRAMMER:
      V1.0/01-93/TKB (USNO/NRL Optical Interfer.) Translate Fortran.
      V1.1/08-93/WTH (USNO/AA) Update to C Standards.
      V1.2/11-03/JAB (USNO/AA) Remove returned value.
      V1.3/01-06/WKP (USNO/AA) Changed 'mode' to 'accuracy'.

   NOTES:
      1. This function is the C version of NOVAS Fortran routine
      'nutate'.

------------------------------------------------------------------------
*/
{
   double cobm, sobm, cobt, sobt, cpsi, spsi, xx, yx, zx, xy, yy, zy,
      xz, yz, zz, oblm, oblt, eqeq, psi, eps;

/*
   Call 'e_tilt' to get the obliquity and nutation angles.
*/

   e_tilt (jd_tdb,accuracy, &oblm,&oblt,&eqeq,&psi,&eps);

   cobm = cos (oblm * DEG2RAD);
   sobm = sin (oblm * DEG2RAD);
   cobt = cos (oblt * DEG2RAD);
   sobt = sin (oblt * DEG2RAD);
   cpsi = cos (psi * ASEC2RAD);
   spsi = sin (psi * ASEC2RAD);

/*
   Nutation rotation matrix follows.
*/

   xx = cpsi;
   yx = -spsi * cobm;
   zx = -spsi * sobm;
   xy = spsi * cobt;
   yy = cpsi * cobm * cobt + sobm * sobt;
   zy = cpsi * sobm * cobt - cobm * sobt;
   xz = spsi * sobt;
   yz = cpsi * cobm * sobt - sobm * cobt;
   zz = cpsi * sobm * sobt + cobm * cobt;

   if (!direction)
   {

/*
   Perform rotation.
*/

      pos2[0] = xx * pos[0] + yx * pos[1] + zx * pos[2];
      pos2[1] = xy * pos[0] + yy * pos[1] + zy * pos[2];
      pos2[2] = xz * pos[0] + yz * pos[1] + zz * pos[2];
   }
    else
   {

/*
   Perform inverse rotation.
*/

      pos2[0] = xx * pos[0] + xy * pos[1] + xz * pos[2];
      pos2[1] = yx * pos[0] + yy * pos[1] + yz * pos[2];
      pos2[2] = zx * pos[0] + zy * pos[1] + zz * pos[2];
   }

   return;
}

/********nutation_angles */

void nutation_angles (double t, short int accuracy,
                      double *dpsi, double *deps)
/*
------------------------------------------------------------------------

   PURPOSE:
      This function returns the values for nutation in longitude and
      nutation in obliquity for a given TDB Julian date.  The nutation
      model selected depends upon the input value of 'accuracy'.  See
      notes below for important details.

   REFERENCES:
      Kaplan, G. (2005), US Naval Observatory Circular 179.

   INPUT
   ARGUMENTS:
      t (double)
         TDB time in Julian centuries since J2000.0
      accuracy (short int)
         Selection for accuracy
            = 0 ... full accuracy
            = 1 ... reduced accuracy

   OUTPUT
   ARGUMENTS:
      dpsi (double)
         Nutation in longitude in arcseconds.
      deps (double)
         Nutation in obliquity in arcseconds.

   RETURNED
   VALUE:
      None.

   GLOBALS
   USED:
      T0, ASEC2RAD       novascon.c

   FUNCTIONS
   CALLED:
      iau2000a           nutation.c
      iau2000b           nutation.c
      nu2000k            nutation.c

   VER./DATE/
   PROGRAMMER:
      V1.0/12-04/JAB (USNO/AA)
      V1.1/01-06/WKP (USNO/AA): Changed 'mode' to 'accuracy'.
      V1.2/02-06/WKP (USNO/AA): Fixed units bug.
      V1.3/01-07/JAB (USNO/AA): Implemented 'low_acc_choice' construct.

   NOTES:
      1. This function selects the nutation model depending first upon
      the input value of 'accuracy'.  If 'accuracy' = 0 (full accuracy),
      the IAU 2000A nutation model is used.  If 'accuracy' = 1 (reduced
      accuracy, the model used depends upon the value of local
      variable 'low_acc_choice', which is set below.
      2. If local variable 'low_acc_choice' = 1 (the default), a
      specially truncated version of IAU 2000A, called 'NU2000K' is
      used.  If 'low_acc_choice' = 2, the IAU 2000B nutation model is
      used.
      3.  See the prologs of the nutation functions in file 'nutation.c'
      for details concerning the models.
      4. This function is the C version of NOVAS Fortran routine
      'nod'.

------------------------------------------------------------------------
*/
{

/*
   Set the value of 'low_acc_choice' according to the rules explained
   under NOTES in the prolog.
*/

   short int low_acc_choice = 1;

   double t1;

   t1 = t * 36525.0;

/*
   High accuracy mode -- use IAU 2000A.
*/

   if (accuracy == 0)
   {
      iau2000a (T0,t1, dpsi,deps);
   }

/*
   Low accuracy mode -- model depends upon value of 'low_acc_choice'.
*/

    else
   {
      switch (low_acc_choice)
      {
         case 2:   /*  use IAU 2000B */
            iau2000b (T0,t1, dpsi,deps);
            break;

         case 1:   /*  use NU2000K  */
         default:
            nu2000k (T0,t1, dpsi,deps);
      }
   }

/*
   Convert output to arcseconds.
*/

   *dpsi /= ASEC2RAD;
   *deps /= ASEC2RAD;

   return;
}

/********fund_args */

void fund_args (double t,

                double a[5])
/*
------------------------------------------------------------------------

   PURPOSE:
      To compute the fundamental arguments (mean elements) of the Sun
      and Moon.

   REFERENCES:
      Simon et al. (1994) Astronomy and Astrophysics 282, 663-683,
         esp. Sections 3.4-3.5.

   INPUT
   ARGUMENTS:
      t (double)
         TDB time in Julian centuries since J2000.0

   OUTPUT
   ARGUMENTS:
      a[5] (double)
         Fundamental arguments, in radians:
          a[0] = l (mean anomaly of the Moon)
          a[1] = l' (mean anomaly of the Sun)
          a[2] = F (mean argument of the latitude of the Moon)
          a[3] = D (mean elongation of the Moon from the Sun)
          a[4] = Omega (mean longitude of the Moon's ascending node);
                 from Simon section 3.4(b.3),
                 precession = 5028.8200 arcsec/cy)

   RETURNED
   VALUE:
      None.

   GLOBALS
   USED:
      ASEC2RAD, ASEC360  novascon.c

   FUNCTIONS
   CALLED:
      fmod               math.h

   VER./DATE/
   PROGRAMMER:
      V1.0/10-97/JAB (USNO/AA)
      V1.1/07-98/JAB (USNO/AA): Place arguments in the range 0-TWOPI
                                radians.
      V1.2/09-03/JAB (USNO/AA): Incorporate function 'norm_ang'.
      V1.3/11-03/JAB (USNO/AA): Update with Simon et al. expressions.
      V1.4/01-06/JAB (USNO/AA): Remove function 'norm_ang'; rewrite for
                                consistency with Fortran.
      V1.5/02-11/WKP (USNO/AA): Clarified a[4] description in prolog.

   NOTES:
      1. This function is the C version of NOVAS Fortran routine
      'funarg'.

------------------------------------------------------------------------
*/
{

   a[0] = fmod (485868.249036 +
             t * (1717915923.2178 +
             t * (        31.8792 +
             t * (         0.051635 +
             t * (       - 0.00024470)))), ASEC360) * ASEC2RAD;

   a[1] = fmod (1287104.79305 +
             t * ( 129596581.0481 +
             t * (       - 0.5532 +
             t * (         0.000136 +
             t * (       - 0.00001149)))), ASEC360) * ASEC2RAD;

   a[2] = fmod (335779.526232 +
             t * (1739527262.8478 +
             t * (      - 12.7512 +
             t * (      -  0.001037 +
             t * (         0.00000417)))), ASEC360) * ASEC2RAD;

   a[3] = fmod (1072260.70369 +
             t * (1602961601.2090 +
             t * (       - 6.3706 +
             t * (         0.006593 +
             t * (       - 0.00003169)))), ASEC360) * ASEC2RAD;

   a[4] = fmod (450160.398036 +
             t * ( - 6962890.5431 +
             t * (         7.4722 +
             t * (         0.007702 +
             t * (       - 0.00005939)))), ASEC360) * ASEC2RAD;

   return;
}

/********mean_obliq */

double mean_obliq (double jd_tdb)
/*
------------------------------------------------------------------------

   PURPOSE:
      To compute the mean obliquity of the ecliptic.

   REFERENCES:
      Capitaine et al. (2003), Astronomy and Astrophysics 412, 567-586.

   INPUT
   ARGUMENTS:
      jd_tdb (double)
         TDB Julian Date.

   OUTPUT
   ARGUMENTS:
      None.

   RETURNED
   VALUE:
      (double)
         Mean obliquity of the ecliptic in arcseconds.

   GLOBALS
   USED:
      T0                 novascon.c

   FUNCTIONS
   CALLED:
      None.

   VER./DATE/
   PROGRAMMER:
      V1.0/12-04/JAB (USNO/AA)
      V2.0/04-06/JAB (USNO/AA) Update the expression for mean obliquity
                               using data from the reference.

   NOTES:
      None.

------------------------------------------------------------------------
*/
{
   double t, epsilon;

/*
   Compute time in Julian centuries from epoch J2000.0.
*/

   t = (jd_tdb - T0) / 36525.0;

/*
   Compute the mean obliquity in arcseconds.  Use expression from the
   reference's eq. (39) with obliquity at J2000.0 taken from eq. (37)
   or Table 8.
*/

   epsilon = (((( -  0.0000000434   * t
                  -  0.000000576  ) * t
                  +  0.00200340   ) * t
                  -  0.0001831    ) * t
                  - 46.836769     ) * t + 84381.406;

   return (epsilon);
}

/********tdb2tt */

void tdb2tt (double tdb_jd,

             double *tt_jd, double *secdiff)
/*
------------------------------------------------------------------------

   PURPOSE:
      Computes the Terrestrial Time (TT) or Terrestrial Dynamical Time
      (TDT) Julian date corresponding to a Barycentric Dynamical Time
      (TDB) Julian date.

   REFERENCES:
      Fairhead, L. & Bretagnon, P. (1990) Astron. & Astrophys. 229, 240.
      Kaplan, G. (2005), US Naval Observatory Circular 179.

   INPUT
   ARGUMENTS:
      tdb_jd (double)
         TDB Julian date.

   OUTPUT
   ARGUMENTS:
      *tt_jd (double)
         TT Julian date.
      *secdiff (double)
         Difference 'tdb_jd'-'tt_jd', in seconds.

   RETURNED
   VALUE:
      None.

   GLOBALS
   USED:
      T0                 novascon.c

   FUNCTIONS
   CALLED:
      sin                math.h

   VER./DATE/
   PROGRAMMER:
      V1.0/07-92/TKB (USNO/NRL Optical Interfer.) Translate Fortran.
      V1.1/08-93/WTH (USNO/AA) Update to C Standards.
      V1.2/06-98/JAB (USNO/AA) Adopt new model (Explanatory Supplement
                               to the Astronomical Almanac, pp. 42-44
                               and p. 316.)
      V1.3/11-03/JAB (USNO/AA) Changed variable names of the input
                               Julian dates to make more descriptive.
      V1.4/01-07/JAB (USNO/AA) Adopt Fairhead & Bretagnon expression.

   NOTES:
      1. Expression used in this function is a truncated form of a
      longer and more precise series given in the first reference.  The
      result is good to about 10 microseconds.
      2. This function is the C version of NOVAS Fortran routine
      'times'.
------------------------------------------------------------------------
*/
{
   double t;

   t = (tdb_jd - T0) / 36525.0;

/*
   Expression given in USNO Circular 179, eq. 2.6.
*/

   *secdiff = 0.001657 * sin ( 628.3076 * t + 6.2401)
            + 0.000022 * sin ( 575.3385 * t + 4.2970)
            + 0.000014 * sin (1256.6152 * t + 6.1969)
            + 0.000005 * sin ( 606.9777 * t + 4.0212)
            + 0.000005 * sin (  52.9691 * t + 0.4444)
            + 0.000002 * sin (  21.3299 * t + 5.5431)
            + 0.000010 * t * sin ( 628.3076 * t + 4.2490);

   *tt_jd = tdb_jd - *secdiff / 86400.0;

    return;
}

/********cio_location */

short int cio_location (double jd_tdb, short int accuracy,

                        double *ra_cio, short int *ref_sys)
/*
------------------------------------------------------------------------

   PURPOSE:
      This function returns the location of the celestial
      intermediate origin (CIO) for a given Julian date, as a
      right ascension with respect to either the GCRS (geocentric ICRS)
      origin or the true equinox of date.  The CIO is always located on
      the true equator (= intermediate equator) of date.

   REFERENCES:
      None.

   INPUT
   ARGUMENTS:
      jd_tdb (double)
         TDB Julian date.
      accuracy (short int)
         Selection for accuracy
            = 0 ... full accuracy
            = 1 ... reduced accuracy

   OUTPUT
   ARGUMENTS:
      *ra_cio (double)
         Right ascension of the CIO, in hours.
      *ref_sys (short int)
         Reference system in which right ascension is given
            = 1 ... GCRS
            = 2 ... True equator and equinox of date.

   RETURNED
   VALUE:
      (short int)
         = 0  ... everything OK.
         = 1  ... unable to allocate memory for the 'cio' array.
         > 10 ... 10 + the error code from function 'cio_array'.

   GLOBALS
   USED:
      None.

   FUNCTIONS
   CALLED:
      cio_array          novas.c
      ira_equinox        novas.c
      fopen              stdio.h
      fclose             stdio.h
      fabs               math.h
      calloc             stdlib.h

   VER./DATE/
   PROGRAMMER:
      V1.0/07-06/JAB (USNO/AA)

   NOTES:
      1. If an external file of CIO right ascensions is available,
      it will be used and 'ref_sys' will be set to 1.  Otherwise an
      internal computation will be used and 'ref_sys' will be set to 2.
      2. The external binary file of CIO right ascensions is assumed
      to be named 'cio_ra.bin'.  Utility program 'cio_file.c', provided
      with the NOVAS-C package, creates this file from a text file also
      provided with NOVAS-C.
      3. This function is the C version of NOVAS Fortran routine
      'cioloc'.

------------------------------------------------------------------------
*/
{
   static short int first_call = 1;
   static short int ref_sys_last = 0;
   static short int use_file = 0;
   short int error = 0;

   long int n_pts = 6;
   long int i, j;

   static double t_last = 0.0;
   static double ra_last;
   double p, eq_origins;

   size_t cio_size;

   static ra_of_cio *cio;

   static FILE *cio_file;

/*
   Check if the input external binary file exists and can be read.
*/

   if (first_call)
   {
      if ((cio_file = fopen ("cio_ra.bin", "rb")) == NULL)
      {
         use_file = 0;
      }
       else
      {
         use_file = 1;
         fclose (cio_file);
      }
   }

/*
   Check if previously computed RA value can be used.
*/

   if ((fabs (jd_tdb - t_last) <= 1.0e-8))
   {
      *ra_cio = ra_last;
      *ref_sys = ref_sys_last;
      return (error = 0);
   }

/*
   Compute the RA of the CIO.
*/

   switch (use_file)
   {

/*
   -----------------------------
   Interpolate values from file.
   -----------------------------
*/

      case 1:

/*
   Allocate memory for the array 'cio'.  This array contains the values
   to be interpolated, extracted from the CIO file.
*/

         if (first_call)
         {
            cio_size = sizeof (ra_of_cio);
            cio = (ra_of_cio *) calloc ((size_t) n_pts, cio_size);
            if (cio == NULL)
               return (error = 1);
             else
               first_call = 0;
         }

/*
   Get array of values to interpolate.
*/

         if ((error = cio_array (jd_tdb,n_pts, cio)) != 0)
         {
            *ra_cio = 0.0;
            return (error += 10);
         }

/*
   Perform Lagrangian interpolation for the RA at 'tdb_jd'.
*/

         *ra_cio = 0.0;
         for (j = 0L; j < n_pts; j++)
         {
            p = 1.0;
            for (i = 0L; i < n_pts; i++)
            {
               if (i != j)
                  p *= ((jd_tdb - cio[i].jd_tdb) /
                       (cio[j].jd_tdb - cio[i].jd_tdb));
            }
            *ra_cio += (p * cio[j].ra_cio);
         }

         *ra_cio /= 54000.0;
         *ref_sys = 1;

         break;

/*
   -------------------------
   Use internal computation.
   -------------------------
*/

      case 0:

/*
   Compute equation of the origins.
*/

         if (first_call)
            first_call = 0;

         eq_origins = ira_equinox (jd_tdb,1,accuracy);

         *ra_cio = -eq_origins;
         *ref_sys = 2;

         break;
   }

   t_last = jd_tdb;
   ra_last = *ra_cio;
   ref_sys_last = *ref_sys;

   return (error);
}

/********cio_basis */

short int cio_basis (double jd_tdb, double ra_cio, short int ref_sys,
                     short int accuracy,

                     double *x, double *y, double *z)
/*
------------------------------------------------------------------------

   PURPOSE:
      To compute the orthonormal basis vectors, with
      respect to the GCRS (geocentric ICRS), of the celestial
      intermediate system defined by the celestial intermediate pole
      (CIP) (in the z direction) and the celestial intermediate origin
      (CIO) (in the x direction).  A TDB Julian date and the right
      ascension of the CIO at that date is required as input.  The
      right ascension of the CIO can be with respect to either the
      GCRS origin or the true equinox of date -- different algorithms
      are used in the two cases.

   REFERENCES:
      Kaplan, G. (2005), US Naval Observatory Circular 179.

   INPUT
   ARGUMENTS:
      jd_tdb (double)
         TDB Julian date of epoch.
      ra_cio (double)
         Right ascension of the CIO at epoch (hours).
      ref_sys (short int)
         Reference system in which right ascension is given (output
         from function 'cio_location')
            = 1 ... GCRS
            = 2 ... True equator and equinox of date.
      accuracy (short int)
         Selection for accuracy
            = 0 ... full accuracy
            = 1 ... reduced accuracy

   OUTPUT
   ARGUMENTS:
      *x (double)
         Unit vector toward the CIO, equatorial rectangular
         coordinates, referred to the GCRS.
      *y (double)
         Unit vector toward the y-direction, equatorial rectangular
         coordinates, referred to the GCRS.
      *z (double)
         Unit vector toward north celestial pole (CIP), equatorial
         rectangular coordinates, referred to the GCRS.

   RETURNED
   VALUE:
      (short int)
         = 0 ... everything OK.
         = 1 ... invalid value of input variable 'ref_sys'.

   GLOBALS
   USED:
      T0, DEG2RAD        novascon.c

   FUNCTIONS
   CALLED:
      nutation           novas.c
      precession         novas.c
      frame_tie          novas.c
      fabs               math.h
      sin                math.h
      cos                math.h
      sqrt               math.h

   VER./DATE/
   PROGRAMMER:
      V1.0/08-04/JAB (USNO/AA)
      V1.1/01-06/WKP (USNO/AA) Changed 'mode' to 'accuracy'.
      V1.2/07-06/JAB (USNA/AA) Incorporate code to use 'ref_sys' input.
      V1.3/06-08/WKP (USNO/AA) Changed value of direction argument in
                               calls to 'nutation' from 1 to -1 for
                               consistency.

   NOTES:
      1. This function effectively constructs the matrix C in eq. (3)
      of the reference.
      2. This function is the C version of NOVAS Fortran routine
      'ciobas'.

------------------------------------------------------------------------
*/
{
   static short int ref_sys_last = 0;
   short int error = 0;
   short int i;

   static double t_last = 0.0;
   static double xx[3], yy[3], zz[3];
   double z0[3] = {0.0, 0.0, 1.0};
   double w0[3], w1[3], w2[3], sinra, cosra, xmag;

/*
   Compute unit vector z toward celestial pole.
*/

   if (((fabs (jd_tdb - t_last) > 1.0e-8)) || (ref_sys != ref_sys_last))
   {
      nutation (jd_tdb,-1,accuracy,z0, w1);
      precession (jd_tdb,w1,T0, w2);
      frame_tie (w2,-1, zz);

      t_last = jd_tdb;
      ref_sys_last = ref_sys;
   }
    else
   {
      for (i = 0; i < 3; i++)
      {
         x[i] = xx[i];
         y[i] = yy[i];
         z[i] = zz[i];
      }
      return (error);
   }

/*
   Now compute unit vectors x and y.  Method used depends on the
   reference system in which right ascension of the CIO is given.
*/

   switch (ref_sys)
   {

/*
   ----------------------------
   RA of CIO expressed in GCRS.
   ----------------------------
*/

      case 1:

/*
   Compute vector x toward CIO in GCRS.
*/

         sinra = sin (ra_cio * 15.0 * DEG2RAD);
         cosra = cos (ra_cio * 15.0 * DEG2RAD);
         xx[0] =  zz[2] * cosra;
         xx[1] =  zz[2] * sinra;
         xx[2] = -zz[0] * cosra - zz[1] * sinra;

/*
   Normalize vector x.
*/

         xmag = sqrt (xx[0] * xx[0] + xx[1] * xx[1] + xx[2] * xx[2]);
         xx[0] /= xmag;
         xx[1] /= xmag;
         xx[2] /= xmag;

/*
   Compute unit vector y orthogonal to x and z (y = z cross x).
*/

         yy[0] = zz[1] * xx[2] - zz[2] * xx[1];
         yy[1] = zz[2] * xx[0] - zz[0] * xx[2];
         yy[2] = zz[0] * xx[1] - zz[1] * xx[0];

         break;

/*
   ----------------------------------------------------------
   RA of CIO expressed in equator-and-equinox of date system.
   ----------------------------------------------------------
*/

      case 2:

/*
   Construct unit vector toward CIO in equator-and-equinox-of-date
   system.
*/

          w0[0] = cos (ra_cio * 15.0 * DEG2RAD);
          w0[1] = sin (ra_cio * 15.0 * DEG2RAD);
          w0[2] = 0.0;

/*
   Rotate the vector into the GCRS to form unit vector x.
*/

          nutation (jd_tdb,-1,accuracy,w0, w1);
          precession (jd_tdb,w1,T0, w2);
          frame_tie (w2,-1, xx);

/*
   Compute unit vector y orthogonal to x and z (y = z cross x).
*/

          yy[0] = zz[1] * xx[2] - zz[2] * xx[1];
          yy[1] = zz[2] * xx[0] - zz[0] * xx[2];
          yy[2] = zz[0] * xx[1] - zz[1] * xx[0];

          break;

/*
   ---------------------------
   Invalid value of 'ref_sys'.
   ---------------------------
*/

      default:

         for (i = 0; i < 3; i++)
         {
            xx[i] = 0.0;
            yy[i] = 0.0;
            zz[i] = 0.0;
         }

         error = 1;
         break;
   }

/*
   Load the x, y, and z arrays.
*/

   for (i = 0; i < 3; i++)
   {
      x[i] = xx[i];
      y[i] = yy[i];
      z[i] = zz[i];
   }

   return (error);
}

/********cio_array */

short int cio_array (double jd_tdb, long int n_pts,

                     ra_of_cio *cio)
/*
------------------------------------------------------------------------

   PURPOSE:
      Given an input TDB Julian date and the number of data points
      desired, this function returns a set of Julian dates and
      corresponding values of the GCRS right ascension of the celestial
      intermediate origin (CIO).  The range of dates is centered (at
      least approximately) on the requested date.  The function obtains
      the data from an external data file.

   REFERENCES:
      None.

   INPUT
   ARGUMENTS:
      jd_tdb (double)
         TDB Julian date.
      n_pts (long int)
         Number of Julian dates and right ascension values requested
         (not less than 2 or more than 20).

   OUTPUT
   ARGUMENTS:
      *cio (struct ra_of_cio)
         An time series (array) of the right ascension of the Celestial
         Intermediate Origin (CIO) with respect to the GCRS (structure
         defined in novas.h).

   RETURNED
   VALUE:
      (short int)
         = 0 ... everything OK
         = 1 ... error opening the 'cio_ra.bin' file.
         = 2 ... 'jd_tdb' not in the range of the CIO file.
         = 3 ... 'n_pts' out of range.
         = 4 ... unable to allocate memory for the internal 't' array.
         = 5 ... unable to allocate memory for the internal 'ra' array.
         = 6 ... 'jd_tdb' is too close to either end of the CIO file;
                 unable to put 'n_pts' data points into the output
                 structure.

   GLOBALS
   USED:
      None.

   FUNCTIONS
   CALLED:
      fopen              stdio.h
      fread              stdio.h
      fclose             stdio.h
      abs                math.h
      free               stdlib.h
      calloc             stdlib.h
      fseek              stdio.h

   VER./DATE/
   PROGRAMMER:
      V1.0/09-04/JAB (USNO/AA)
      V1.1/12-05/WKP (USNO/AA) Changed struct type from 'cio_ra' to
                               'ra_of_cio' to avoid conflicts.
      V1.2/02-08/JAB (USNO/AA) Fix file-read strategy "Case 2" and
                               improve documentation.

   NOTES:
      1. This function assumes that binary, random-access file
      'cio_ra.bin' has been created and is in the same directory as
      your executable.  This file is created by program 'cio_file.c',
      included in the NOVAS-C package.  On the first call to this
      function, file 'cio_ra.bin' is opened in read mode.

------------------------------------------------------------------------
*/
{
   static short int first_call = 1;
   short int error = 0;

   static long int last_index_rec = -50L;
   static long int last_n_pts = 0L;
   static long int header_size, record_size, n_recs;
   long int min_pts = 2;
   long int max_pts = 20;
   long int  del_n_pts, index_rec, half_int, lo_limit, hi_limit,
      del_index, abs_del_index, bytes_to_lo, n_swap, n_read, i, j;

   static double jd_beg, jd_end, t_int, *t, *ra;
   double t_temp, ra_temp;

   static size_t double_size, long_size;

   static FILE *cio_file;

/*
   Set the sizes of the file header and data records, open the CIO file,
   and read the file header on the first call to this function.
*/

   if (first_call)
   {
      double_size = sizeof (double);
      long_size = sizeof (long int);
      header_size = (long) ((size_t) 3 * double_size + long_size);
      record_size = (long) ((size_t) 2 * double_size);

/*
   Open the input (binary, random-access) file.
*/

      if ((cio_file = fopen ("cio_ra.bin", "rb")) == NULL)
         return (error = 1);

/*
   Read the file header.
*/

      fread (&jd_beg, double_size, (size_t) 1, cio_file);
      fread (&jd_end, double_size, (size_t) 1, cio_file);
      fread (&t_int, double_size, (size_t) 1, cio_file);
      fread (&n_recs, long_size, (size_t) 1, cio_file);
   }

/*
   Check the input data against limits.
*/

   if ((jd_tdb < jd_beg) || (jd_tdb > jd_end))
      return (error = 2);

   if ((n_pts < min_pts) || (n_pts > max_pts))
      return (error = 3);

/*
   Calculate the difference between the current value of 'n_pts' and
   the last value of 'n_pts'.
*/

   del_n_pts = abs (n_pts - last_n_pts);

/*
   Allocate memory for the 't' and 'ra' arrays.
*/

   if (del_n_pts != 0L)
   {
      if (!first_call)
      {
         free (t);
         free (ra);
      }

      t = (double *) calloc ((size_t) n_pts, double_size);
      if (t == NULL )
      {
         fclose (cio_file);
         return (error = 4);
      }

      ra = (double *) calloc ((size_t) n_pts, double_size);
      if (ra == NULL )
      {
         free (t);
         fclose (cio_file);
         return (error = 5);
      }

      first_call = 0;
   }

/*
   Calculate the record number of the record immediately preceding
   the date of interest: the "index record".
*/

   index_rec = (long int) ((jd_tdb - jd_beg) / t_int) + 1L;

/*
   Test the range of 'n_pts' values centered on 'index_rec' to be sure
   the range of values requested falls within the file limits.
*/

   half_int = (n_pts / 2L) - 1L;
   lo_limit = index_rec - half_int;
   hi_limit = index_rec + (n_pts - half_int - 1L);

   if ((lo_limit < 1L) || (hi_limit > n_recs))
      return (error = 6);

/*
   Compute the number of bytes from the beginning of the file to
   the 'lo_limit'.
*/

   bytes_to_lo = header_size + (lo_limit - 1L) * record_size;

/*
   Compare the current index record with the previous index record.
*/

   del_index = index_rec - last_index_rec;
   abs_del_index = abs (del_index);

/*
   Determine the file read strategy.
*/

/*
   Case 1: The input value of 'n_pts' changed since the last entry,
   or there are no data in the current arrays that can be re-used in the
   new arrays.  In this case, read all new data points into the arrays.
*/

   if ((abs_del_index > n_pts) || (del_n_pts != 0))
   {
      fseek (cio_file, bytes_to_lo, SEEK_SET);

      for (i = 0L; i < n_pts; i++)
      {
         fread (&t[i], double_size, (size_t) 1, cio_file);
         fread (&ra[i], double_size, (size_t) 1, cio_file);
      }
   }

/*
   Case 2: The new index is close enough to the previous index that
   there are some data in the current arrays that can be re-used
   in the new arrays.  The remaining data will be read from the CIO
   file.

   Note that if the new index is the same as the previous index (i.e.,
   'del_index' == 0), neither Case 2a nor 2b is satisfied, and the
   program flow goes directly to load the output arrays with the same
   values as in the current arrays.
*/

    else if ((abs_del_index <= n_pts) && (del_n_pts == 0))
   {
      n_swap = abs (n_pts - abs_del_index);
      n_read = abs_del_index;

/*
   Case 2a: The new index is less than the previous one.  Put the "old"
   data at the end of the new arrays, and read "new" data into the
   beginning of the new arrays.
*/

      if (del_index < 0L)
      {
         for (i = 0L; i < n_swap; i++)
         {
            t_temp = t[i];
            ra_temp = ra[i];

            j = i + abs_del_index;
            t[j] = t_temp;
            ra[j] = ra_temp;
         }

         fseek (cio_file, bytes_to_lo, SEEK_SET);

         for (i = 0L; i < n_read; i++)
         {
            fread (&t[i], double_size, (size_t) 1, cio_file);
            fread (&ra[i], double_size, (size_t) 1, cio_file);
         }
      }

/*
   Case 2b: The new index is greater than the previous one.  Put the
   "old" data at the beginning of the new arrays, and read "new" data
   into the end of the new arrays.
*/

       else if (del_index > 0L)
      {
         for (i = 0L; i < n_swap; i++)
         {
            j = i + abs_del_index;
            t_temp = t[j];
            ra_temp = ra[j];

            t[i] = t_temp;
            ra[i] = ra_temp;
         }

         fseek (cio_file, bytes_to_lo + (n_swap * record_size),
            SEEK_SET);

         j = i++;
         for (i = j; i < n_pts; i++)
         {
            fread (&t[i], double_size, (size_t) 1, cio_file);
            fread (&ra[i], double_size, (size_t) 1, cio_file);
         }
      }
   }

/*
   Load the output 'cio' array with the values in the 't' and 'ra'
   arrays.

   Note that if the input value of 'n_pts' has not changed since the
   last entry, all data in the current arrays can be re-used in
   the new arrays. The if statements above are bypassed and the new
   arrays are the same as the current arrays.
*/

   for (i = 0L; i < n_pts; i++)
   {
      cio[i].jd_tdb = t[i];
      cio[i].ra_cio = ra[i];
   }

/*
   Set values of 'last_index_rec' and 'last_n_pts'.
*/

   last_index_rec = index_rec;
   last_n_pts = n_pts;

   return (error);
}

/********ira_equinox */

double ira_equinox (double jd_tdb, short int equinox,
                    short int accuracy)
/*
------------------------------------------------------------------------

   PURPOSE:
      To compute the intermediate right ascension of the equinox at
      the input Julian date, using an analytical expression for the
      accumulated precession in right ascension.  For the true equinox,
      the result is the equation of the origins.

   REFERENCES:
      Capitaine, N. et al. (2003), Astronomy and Astrophysics 412,
         567-586, eq. (42).

   INPUT
   ARGUMENTS:
      jd_tdb (double)
         TDB Julian date.
      equinox (short int)
         Equinox selection flag:
            = 0 ... mean equinox
            = 1 ... true equinox.
      accuracy (short int)
         Selection for accuracy
            = 0 ... full accuracy
            = 1 ... reduced accuracy

   OUTPUT
   ARGUMENTS:
      None.

   RETURNED
   VALUE:
      (double)
         Intermediate right ascension of the equinox, in hours (+ or -).
         If 'equinox' = 1 (i.e true equinox), then the returned value is
         the equation of the origins.

   GLOBALS
   USED:
      T0                 novascon.c

   FUNCTIONS
   CALLED:
      e_tilt             novas.c
      fabs               math.h

   VER./DATE/
   PROGRAMMER:
      V1.0/07-06/JAB (USNO/AA)

   NOTES:
      1. This function is the C version of NOVAS Fortran routine
      'eqxra'.

------------------------------------------------------------------------
*/
{
   static short int acc_last = 99;

   static double t_last = 0.0;
   static double eq_eq = 0.0;
   double t, u, v, w, x, prec_ra, ra_eq;

/*
   Compute time in Julian centuries.
*/

   t = (jd_tdb - T0 ) / 36525.0;

/*
   For the true equinox, obtain the equation of the equinoxes in time
   seconds, which includes the 'complementary terms'.
*/

   if (equinox == 1)
   {
      if (((fabs (jd_tdb - t_last)) > 1.0e-8) || (accuracy != acc_last))
      {
         e_tilt (jd_tdb,accuracy, &u, &v, &eq_eq, &w, &x);
         t_last = jd_tdb;
         acc_last = accuracy;
      }
   }
    else
   {
      eq_eq = 0.0;
   }

/*
   Precession in RA in arcseconds taken from the reference.
*/

   prec_ra = 0.014506 +
      (((( -    0.0000000368   * t
           -    0.000029956  ) * t
           -    0.00000044   ) * t
           +    1.3915817    ) * t
           + 4612.156534     ) * t;

   ra_eq = - (prec_ra / 15.0 + eq_eq) / 3600.0;

   return (ra_eq);
}

/********julian_date */

double julian_date (short int year, short int month, short int day,
                    double hour)
/*
------------------------------------------------------------------------

   PURPOSE:
      This function will compute the Julian date for a given calendar
      date (year, month, day, hour).

   REFERENCES:
      Fliegel, H. & Van Flandern, T.  Comm. of the ACM, Vol. 11, No. 10,
         October 1968, p. 657.

   INPUT
   ARGUMENTS:
      year (short int)
         Year.
      month (short int)
         Month number.
      day (short int)
         Day-of-month.
      hour (double)
         Hour-of-day.

   OUTPUT
   ARGUMENTS:
      None.

   RETURNED
   VALUE:
      (double)
         Julian date.

   GLOBALS
   USED:
      None.

   FUNCTIONS
   CALLED:
      None.

   VER./DATE/
   PROGRAMMER:
      V1.0/06-98/JAB (USNO/AA)
      V1.1/03-08/WKP (USNO/AA) Updated prolog.

   NOTES:
      1. This function is the C version of NOVAS Fortran routine
      'juldat'.
      2. This function makes no checks for a valid input calendar
      date.
      3. Input calendar date must be Gregorian.
      4. Input time value can be based on any UT-like time scale
      (UTC, UT1, TT, etc.) - output Julian date will have the same basis.
------------------------------------------------------------------------
*/
{
   long int jd12h;

   double tjd;

   jd12h = (long) day - 32075L + 1461L * ((long) year + 4800L
      + ((long) month - 14L) / 12L) / 4L
      + 367L * ((long) month - 2L - ((long) month - 14L) / 12L * 12L)
      / 12L - 3L * (((long) year + 4900L + ((long) month - 14L) / 12L)
      / 100L) / 4L;
   tjd = (double) jd12h - 0.5 + hour / 24.0;

   return (tjd);
}

/********norm_ang */

double norm_ang (double angle)
/*
------------------------------------------------------------------------

   PURPOSE:
      Normalize angle into the range 0 <= angle < (2 * pi).

   REFERENCES:
      None.

   INPUT
   ARGUMENTS:
      angle (double)
         Input angle (radians).

   OUTPUT
   ARGUMENTS:
      None.

   RETURNED
   VALUE:
      (double)
          The input angle, normalized as described above (radians).

   GLOBALS
   USED:
      TWOPI              novascon.c

   FUNCTIONS
   CALLED:
      fmod               math.h

   VER./DATE/
   PROGRAMMER:
      V1.0/09-03/JAB (USNO/AA)

   NOTES:
      None.

------------------------------------------------------------------------
*/
{
   double a;

   a = fmod (angle,TWOPI);
   if (a < 0.0)
         a += TWOPI;

   return (a);
}




////////////////////////////////////////////////////////////////////////////////
//// 
//// Functions for nutation_angles(), from nutation.c 
////

/*
   Naval Observatory Vector Astrometry Software (NOVAS)
   C Edition, Version 3.1
   
   nutation.c: Nutation models

   U. S. Naval Observatory
   Astronomical Applications Dept.
   Washington, DC 
   http://www.usno.navy.mil/USNO/astronomical-applications
*/

////#ifndef _NOVAS_
////   #include "novas.h"
////#endif

/********iau2000a */

void iau2000a (double jd_high, double jd_low,

               double *dpsi, double *deps)
/*
------------------------------------------------------------------------

   PURPOSE:
      To compute the forced nutation of the non-rigid Earth based on
      the IAU 2000A nutation model.

   REFERENCES:
      IERS Conventions (2003), Chapter 5.
      Simon et al. (1994) Astronomy and Astrophysics 282, 663-683,
         esp. Sections 3.4-3.5.

   INPUT
   ARGUMENTS:
      jd_high (double)
         High-order part of TT Julian date.
      jd_low (double)
         Low-order part of TT Julian date.

   OUTPUT
   ARGUMENTS:
      *dpsi (double)
         Nutation (luni-solar + planetary) in longitude, in radians.
      *deps (double)
         Nutation (luni-solar + planetary) in obliquity, in radians.

   RETURNED
   VALUE:
      None.

   GLOBALS
   USED:
      T0, ASEC2RAD, TWOPI

   FUNCTIONS
   CALLED:
      fund_args    novas.c
      fmod         math.h
      sin          math.h
      cos          math.h

   VER./DATE/
   PROGRAMMER:
      V1.0/03-04/JAB (USNO/AA)
      V1.1/12-10/JAB (USNO/AA): Implement static storage class for const
                                arrays.
      V1.2/03-11/WKP (USNO/AA): Added braces to 2-D array initialization
                                to quiet gcc warnings.

   NOTES:
     1. The IAU 2000A nutation model is MHB_2000 without the free core
     nutation and without the corrections to Lieske precession.
     2. This function is the "C" version of NOVAS Fortran routine
     'nu2000a'.

------------------------------------------------------------------------
*/
{
   short int i;

   double t, a[5], dp, de, arg, sarg, carg, factor, dpsils, depsls,
      al, alsu, af, ad, aom, alme, alve, alea, alma, alju, alsa, alur,
      alne, apa, dpsipl, depspl;

/*
   Luni-Solar argument multipliers:
       L     L'    F     D     Om
*/

   static const short int nals_t[678][5] = {
      { 0,    0,    0,    0,    1},
      { 0,    0,    2,   -2,    2},
      { 0,    0,    2,    0,    2},
      { 0,    0,    0,    0,    2},
      { 0,    1,    0,    0,    0},
      { 0,    1,    2,   -2,    2},
      { 1,    0,    0,    0,    0},
      { 0,    0,    2,    0,    1},
      { 1,    0,    2,    0,    2},
      { 0,   -1,    2,   -2,    2},
      { 0,    0,    2,   -2,    1},
      {-1,    0,    2,    0,    2},
      {-1,    0,    0,    2,    0},
      { 1,    0,    0,    0,    1},
      {-1,    0,    0,    0,    1},
      {-1,    0,    2,    2,    2},
      { 1,    0,    2,    0,    1},
      {-2,    0,    2,    0,    1},
      { 0,    0,    0,    2,    0},
      { 0,    0,    2,    2,    2},
      { 0,   -2,    2,   -2,    2},
      {-2,    0,    0,    2,    0},
      { 2,    0,    2,    0,    2},
      { 1,    0,    2,   -2,    2},
      {-1,    0,    2,    0,    1},
      { 2,    0,    0,    0,    0},
      { 0,    0,    2,    0,    0},
      { 0,    1,    0,    0,    1},
      {-1,    0,    0,    2,    1},
      { 0,    2,    2,   -2,    2},
      { 0,    0,   -2,    2,    0},
      { 1,    0,    0,   -2,    1},
      { 0,   -1,    0,    0,    1},
      {-1,    0,    2,    2,    1},
      { 0,    2,    0,    0,    0},
      { 1,    0,    2,    2,    2},
      {-2,    0,    2,    0,    0},
      { 0,    1,    2,    0,    2},
      { 0,    0,    2,    2,    1},
      { 0,   -1,    2,    0,    2},
      { 0,    0,    0,    2,    1},
      { 1,    0,    2,   -2,    1},
      { 2,    0,    2,   -2,    2},
      {-2,    0,    0,    2,    1},
      { 2,    0,    2,    0,    1},
      { 0,   -1,    2,   -2,    1},
      { 0,    0,    0,   -2,    1},
      {-1,   -1,    0,    2,    0},
      { 2,    0,    0,   -2,    1},
      { 1,    0,    0,    2,    0},
      { 0,    1,    2,   -2,    1},
      { 1,   -1,    0,    0,    0},
      {-2,    0,    2,    0,    2},
      { 3,    0,    2,    0,    2},
      { 0,   -1,    0,    2,    0},
      { 1,   -1,    2,    0,    2},
      { 0,    0,    0,    1,    0},
      {-1,   -1,    2,    2,    2},
      {-1,    0,    2,    0,    0},
      { 0,   -1,    2,    2,    2},
      {-2,    0,    0,    0,    1},
      { 1,    1,    2,    0,    2},
      { 2,    0,    0,    0,    1},
      {-1,    1,    0,    1,    0},
      { 1,    1,    0,    0,    0},
      { 1,    0,    2,    0,    0},
      {-1,    0,    2,   -2,    1},
      { 1,    0,    0,    0,    2},
      {-1,    0,    0,    1,    0},
      { 0,    0,    2,    1,    2},
      {-1,    0,    2,    4,    2},
      {-1,    1,    0,    1,    1},
      { 0,   -2,    2,   -2,    1},
      { 1,    0,    2,    2,    1},
      {-2,    0,    2,    2,    2},
      {-1,    0,    0,    0,    2},
      { 1,    1,    2,   -2,    2},
      {-2,    0,    2,    4,    2},
      {-1,    0,    4,    0,    2},
      { 2,    0,    2,   -2,    1},
      { 2,    0,    2,    2,    2},
      { 1,    0,    0,    2,    1},
      { 3,    0,    0,    0,    0},
      { 3,    0,    2,   -2,    2},
      { 0,    0,    4,   -2,    2},
      { 0,    1,    2,    0,    1},
      { 0,    0,   -2,    2,    1},
      { 0,    0,    2,   -2,    3},
      {-1,    0,    0,    4,    0},
      { 2,    0,   -2,    0,    1},
      {-2,    0,    0,    4,    0},
      {-1,   -1,    0,    2,    1},
      {-1,    0,    0,    1,    1},
      { 0,    1,    0,    0,    2},
      { 0,    0,   -2,    0,    1},
      { 0,   -1,    2,    0,    1},
      { 0,    0,    2,   -1,    2},
      { 0,    0,    2,    4,    2},
      {-2,   -1,    0,    2,    0},
      { 1,    1,    0,   -2,    1},
      {-1,    1,    0,    2,    0},
      {-1,    1,    0,    1,    2},
      { 1,   -1,    0,    0,    1},
      { 1,   -1,    2,    2,    2},
      {-1,    1,    2,    2,    2},
      { 3,    0,    2,    0,    1},
      { 0,    1,   -2,    2,    0},
      {-1,    0,    0,   -2,    1},
      { 0,    1,    2,    2,    2},
      {-1,   -1,    2,    2,    1},
      { 0,   -1,    0,    0,    2},
      { 1,    0,    2,   -4,    1},
      {-1,    0,   -2,    2,    0},
      { 0,   -1,    2,    2,    1},
      { 2,   -1,    2,    0,    2},
      { 0,    0,    0,    2,    2},
      { 1,   -1,    2,    0,    1},
      {-1,    1,    2,    0,    2},
      { 0,    1,    0,    2,    0},
      { 0,   -1,   -2,    2,    0},
      { 0,    3,    2,   -2,    2},
      { 0,    0,    0,    1,    1},
      {-1,    0,    2,    2,    0},
      { 2,    1,    2,    0,    2},
      { 1,    1,    0,    0,    1},
      { 1,    1,    2,    0,    1},
      { 2,    0,    0,    2,    0},
      { 1,    0,   -2,    2,    0},
      {-1,    0,    0,    2,    2},
      { 0,    1,    0,    1,    0},
      { 0,    1,    0,   -2,    1},
      {-1,    0,    2,   -2,    2},
      { 0,    0,    0,   -1,    1},
      {-1,    1,    0,    0,    1},
      { 1,    0,    2,   -1,    2},
      { 1,   -1,    0,    2,    0},
      { 0,    0,    0,    4,    0},
      { 1,    0,    2,    1,    2},
      { 0,    0,    2,    1,    1},
      { 1,    0,    0,   -2,    2},
      {-1,    0,    2,    4,    1},
      { 1,    0,   -2,    0,    1},
      { 1,    1,    2,   -2,    1},
      { 0,    0,    2,    2,    0},
      {-1,    0,    2,   -1,    1},
      {-2,    0,    2,    2,    1},
      { 4,    0,    2,    0,    2},
      { 2,   -1,    0,    0,    0},
      { 2,    1,    2,   -2,    2},
      { 0,    1,    2,    1,    2},
      { 1,    0,    4,   -2,    2},
      {-1,   -1,    0,    0,    1},
      { 0,    1,    0,    2,    1},
      {-2,    0,    2,    4,    1},
      { 2,    0,    2,    0,    0},
      { 1,    0,    0,    1,    0},
      {-1,    0,    0,    4,    1},
      {-1,    0,    4,    0,    1},
      { 2,    0,    2,    2,    1},
      { 0,    0,    2,   -3,    2},
      {-1,   -2,    0,    2,    0},
      { 2,    1,    0,    0,    0},
      { 0,    0,    4,    0,    2},
      { 0,    0,    0,    0,    3},
      { 0,    3,    0,    0,    0},
      { 0,    0,    2,   -4,    1},
      { 0,   -1,    0,    2,    1},
      { 0,    0,    0,    4,    1},
      {-1,   -1,    2,    4,    2},
      { 1,    0,    2,    4,    2},
      {-2,    2,    0,    2,    0},
      {-2,   -1,    2,    0,    1},
      {-2,    0,    0,    2,    2},
      {-1,   -1,    2,    0,    2},
      { 0,    0,    4,   -2,    1},
      { 3,    0,    2,   -2,    1},
      {-2,   -1,    0,    2,    1},
      { 1,    0,    0,   -1,    1},
      { 0,   -2,    0,    2,    0},
      {-2,    0,    0,    4,    1},
      {-3,    0,    0,    0,    1},
      { 1,    1,    2,    2,    2},
      { 0,    0,    2,    4,    1},
      { 3,    0,    2,    2,    2},
      {-1,    1,    2,   -2,    1},
      { 2,    0,    0,   -4,    1},
      { 0,    0,    0,   -2,    2},
      { 2,    0,    2,   -4,    1},
      {-1,    1,    0,    2,    1},
      { 0,    0,    2,   -1,    1},
      { 0,   -2,    2,    2,    2},
      { 2,    0,    0,    2,    1},
      { 4,    0,    2,   -2,    2},
      { 2,    0,    0,   -2,    2},
      { 0,    2,    0,    0,    1},
      { 1,    0,    0,   -4,    1},
      { 0,    2,    2,   -2,    1},
      {-3,    0,    0,    4,    0},
      {-1,    1,    2,    0,    1},
      {-1,   -1,    0,    4,    0},
      {-1,   -2,    2,    2,    2},
      {-2,   -1,    2,    4,    2},
      { 1,   -1,    2,    2,    1},
      {-2,    1,    0,    2,    0},
      {-2,    1,    2,    0,    1},
      { 2,    1,    0,   -2,    1},
      {-3,    0,    2,    0,    1},
      {-2,    0,    2,   -2,    1},
      {-1,    1,    0,    2,    2},
      { 0,   -1,    2,   -1,    2},
      {-1,    0,    4,   -2,    2},
      { 0,   -2,    2,    0,    2},
      {-1,    0,    2,    1,    2},
      { 2,    0,    0,    0,    2},
      { 0,    0,    2,    0,    3},
      {-2,    0,    4,    0,    2},
      {-1,    0,   -2,    0,    1},
      {-1,    1,    2,    2,    1},
      { 3,    0,    0,    0,    1},
      {-1,    0,    2,    3,    2},
      { 2,   -1,    2,    0,    1},
      { 0,    1,    2,    2,    1},
      { 0,   -1,    2,    4,    2},
      { 2,   -1,    2,    2,    2},
      { 0,    2,   -2,    2,    0},
      {-1,   -1,    2,   -1,    1},
      { 0,   -2,    0,    0,    1},
      { 1,    0,    2,   -4,    2},
      { 1,   -1,    0,   -2,    1},
      {-1,   -1,    2,    0,    1},
      { 1,   -1,    2,   -2,    2},
      {-2,   -1,    0,    4,    0},
      {-1,    0,    0,    3,    0},
      {-2,   -1,    2,    2,    2},
      { 0,    2,    2,    0,    2},
      { 1,    1,    0,    2,    0},
      { 2,    0,    2,   -1,    2},
      { 1,    0,    2,    1,    1},
      { 4,    0,    0,    0,    0},
      { 2,    1,    2,    0,    1},
      { 3,   -1,    2,    0,    2},
      {-2,    2,    0,    2,    1},
      { 1,    0,    2,   -3,    1},
      { 1,    1,    2,   -4,    1},
      {-1,   -1,    2,   -2,    1},
      { 0,   -1,    0,   -1,    1},
      { 0,   -1,    0,   -2,    1},
      {-2,    0,    0,    0,    2},
      {-2,    0,   -2,    2,    0},
      {-1,    0,   -2,    4,    0},
      { 1,   -2,    0,    0,    0},
      { 0,    1,    0,    1,    1},
      {-1,    2,    0,    2,    0},
      { 1,   -1,    2,   -2,    1},
      { 1,    2,    2,   -2,    2},
      { 2,   -1,    2,   -2,    2},
      { 1,    0,    2,   -1,    1},
      { 2,    1,    2,   -2,    1},
      {-2,    0,    0,   -2,    1},
      { 1,   -2,    2,    0,    2},
      { 0,    1,    2,    1,    1},
      { 1,    0,    4,   -2,    1},
      {-2,    0,    4,    2,    2},
      { 1,    1,    2,    1,    2},
      { 1,    0,    0,    4,    0},
      { 1,    0,    2,    2,    0},
      { 2,    0,    2,    1,    2},
      { 3,    1,    2,    0,    2},
      { 4,    0,    2,    0,    1},
      {-2,   -1,    2,    0,    0},
      { 0,    1,   -2,    2,    1},
      { 1,    0,   -2,    1,    0},
      { 0,   -1,   -2,    2,    1},
      { 2,   -1,    0,   -2,    1},
      {-1,    0,    2,   -1,    2},
      { 1,    0,    2,   -3,    2},
      { 0,    1,    2,   -2,    3},
      { 0,    0,    2,   -3,    1},
      {-1,    0,   -2,    2,    1},
      { 0,    0,    2,   -4,    2},
      {-2,    1,    0,    0,    1},
      {-1,    0,    0,   -1,    1},
      { 2,    0,    2,   -4,    2},
      { 0,    0,    4,   -4,    4},
      { 0,    0,    4,   -4,    2},
      {-1,   -2,    0,    2,    1},
      {-2,    0,    0,    3,    0},
      { 1,    0,   -2,    2,    1},
      {-3,    0,    2,    2,    2},
      {-3,    0,    2,    2,    1},
      {-2,    0,    2,    2,    0},
      { 2,   -1,    0,    0,    1},
      {-2,    1,    2,    2,    2},
      { 1,    1,    0,    1,    0},
      { 0,    1,    4,   -2,    2},
      {-1,    1,    0,   -2,    1},
      { 0,    0,    0,   -4,    1},
      { 1,   -1,    0,    2,    1},
      { 1,    1,    0,    2,    1},
      {-1,    2,    2,    2,    2},
      { 3,    1,    2,   -2,    2},
      { 0,   -1,    0,    4,    0},
      { 2,   -1,    0,    2,    0},
      { 0,    0,    4,    0,    1},
      { 2,    0,    4,   -2,    2},
      {-1,   -1,    2,    4,    1},
      { 1,    0,    0,    4,    1},
      { 1,   -2,    2,    2,    2},
      { 0,    0,    2,    3,    2},
      {-1,    1,    2,    4,    2},
      { 3,    0,    0,    2,    0},
      {-1,    0,    4,    2,    2},
      { 1,    1,    2,    2,    1},
      {-2,    0,    2,    6,    2},
      { 2,    1,    2,    2,    2},
      {-1,    0,    2,    6,    2},
      { 1,    0,    2,    4,    1},
      { 2,    0,    2,    4,    2},
      { 1,    1,   -2,    1,    0},
      {-3,    1,    2,    1,    2},
      { 2,    0,   -2,    0,    2},
      {-1,    0,    0,    1,    2},
      {-4,    0,    2,    2,    1},
      {-1,   -1,    0,    1,    0},
      { 0,    0,   -2,    2,    2},
      { 1,    0,    0,   -1,    2},
      { 0,   -1,    2,   -2,    3},
      {-2,    1,    2,    0,    0},
      { 0,    0,    2,   -2,    4},
      {-2,   -2,    0,    2,    0},
      {-2,    0,   -2,    4,    0},
      { 0,   -2,   -2,    2,    0},
      { 1,    2,    0,   -2,    1},
      { 3,    0,    0,   -4,    1},
      {-1,    1,    2,   -2,    2},
      { 1,   -1,    2,   -4,    1},
      { 1,    1,    0,   -2,    2},
      {-3,    0,    2,    0,    0},
      {-3,    0,    2,    0,    2},
      {-2,    0,    0,    1,    0},
      { 0,    0,   -2,    1,    0},
      {-3,    0,    0,    2,    1},
      {-1,   -1,   -2,    2,    0},
      { 0,    1,    2,   -4,    1},
      { 2,    1,    0,   -4,    1},
      { 0,    2,    0,   -2,    1},
      { 1,    0,    0,   -3,    1},
      {-2,    0,    2,   -2,    2},
      {-2,   -1,    0,    0,    1},
      {-4,    0,    0,    2,    0},
      { 1,    1,    0,   -4,    1},
      {-1,    0,    2,   -4,    1},
      { 0,    0,    4,   -4,    1},
      { 0,    3,    2,   -2,    2},
      {-3,   -1,    0,    4,    0},
      {-3,    0,    0,    4,    1},
      { 1,   -1,   -2,    2,    0},
      {-1,   -1,    0,    2,    2},
      { 1,   -2,    0,    0,    1},
      { 1,   -1,    0,    0,    2},
      { 0,    0,    0,    1,    2},
      {-1,   -1,    2,    0,    0},
      { 1,   -2,    2,   -2,    2},
      { 0,   -1,    2,   -1,    1},
      {-1,    0,    2,    0,    3},
      { 1,    1,    0,    0,    2},
      {-1,    1,    2,    0,    0},
      { 1,    2,    0,    0,    0},
      {-1,    2,    2,    0,    2},
      {-1,    0,    4,   -2,    1},
      { 3,    0,    2,   -4,    2},
      { 1,    2,    2,   -2,    1},
      { 1,    0,    4,   -4,    2},
      {-2,   -1,    0,    4,    1},
      { 0,   -1,    0,    2,    2},
      {-2,    1,    0,    4,    0},
      {-2,   -1,    2,    2,    1},
      { 2,    0,   -2,    2,    0},
      { 1,    0,    0,    1,    1},
      { 0,    1,    0,    2,    2},
      { 1,   -1,    2,   -1,    2},
      {-2,    0,    4,    0,    1},
      { 2,    1,    0,    0,    1},
      { 0,    1,    2,    0,    0},
      { 0,   -1,    4,   -2,    2},
      { 0,    0,    4,   -2,    4},
      { 0,    2,    2,    0,    1},
      {-3,    0,    0,    6,    0},
      {-1,   -1,    0,    4,    1},
      { 1,   -2,    0,    2,    0},
      {-1,    0,    0,    4,    2},
      {-1,   -2,    2,    2,    1},
      {-1,    0,    0,   -2,    2},
      { 1,    0,   -2,   -2,    1},
      { 0,    0,   -2,   -2,    1},
      {-2,    0,   -2,    0,    1},
      { 0,    0,    0,    3,    1},
      { 0,    0,    0,    3,    0},
      {-1,    1,    0,    4,    0},
      {-1,   -1,    2,    2,    0},
      {-2,    0,    2,    3,    2},
      { 1,    0,    0,    2,    2},
      { 0,   -1,    2,    1,    2},
      { 3,   -1,    0,    0,    0},
      { 2,    0,    0,    1,    0},
      { 1,   -1,    2,    0,    0},
      { 0,    0,    2,    1,    0},
      { 1,    0,    2,    0,    3},
      { 3,    1,    0,    0,    0},
      { 3,   -1,    2,   -2,    2},
      { 2,    0,    2,   -1,    1},
      { 1,    1,    2,    0,    0},
      { 0,    0,    4,   -1,    2},
      { 1,    2,    2,    0,    2},
      {-2,    0,    0,    6,    0},
      { 0,   -1,    0,    4,    1},
      {-2,   -1,    2,    4,    1},
      { 0,   -2,    2,    2,    1},
      { 0,   -1,    2,    2,    0},
      {-1,    0,    2,    3,    1},
      {-2,    1,    2,    4,    2},
      { 2,    0,    0,    2,    2},
      { 2,   -2,    2,    0,    2},
      {-1,    1,    2,    3,    2},
      { 3,    0,    2,   -1,    2},
      { 4,    0,    2,   -2,    1},
      {-1,    0,    0,    6,    0},
      {-1,   -2,    2,    4,    2},
      {-3,    0,    2,    6,    2},
      {-1,    0,    2,    4,    0},
      { 3,    0,    0,    2,    1},
      { 3,   -1,    2,    0,    1},
      { 3,    0,    2,    0,    0},
      { 1,    0,    4,    0,    2},
      { 5,    0,    2,   -2,    2},
      { 0,   -1,    2,    4,    1},
      { 2,   -1,    2,    2,    1},
      { 0,    1,    2,    4,    2},
      { 1,   -1,    2,    4,    2},
      { 3,   -1,    2,    2,    2},
      { 3,    0,    2,    2,    1},
      { 5,    0,    2,    0,    2},
      { 0,    0,    2,    6,    2},
      { 4,    0,    2,    2,    2},
      { 0,   -1,    1,   -1,    1},
      {-1,    0,    1,    0,    3},
      { 0,   -2,    2,   -2,    3},
      { 1,    0,   -1,    0,    1},
      { 2,   -2,    0,   -2,    1},
      {-1,    0,    1,    0,    2},
      {-1,    0,    1,    0,    1},
      {-1,   -1,    2,   -1,    2},
      {-2,    2,    0,    2,    2},
      {-1,    0,    1,    0,    0},
      {-4,    1,    2,    2,    2},
      {-3,    0,    2,    1,    1},
      {-2,   -1,    2,    0,    2},
      { 1,    0,   -2,    1,    1},
      { 2,   -1,   -2,    0,    1},
      {-4,    0,    2,    2,    0},
      {-3,    1,    0,    3,    0},
      {-1,    0,   -1,    2,    0},
      { 0,   -2,    0,    0,    2},
      { 0,   -2,    0,    0,    2},
      {-3,    0,    0,    3,    0},
      {-2,   -1,    0,    2,    2},
      {-1,    0,   -2,    3,    0},
      {-4,    0,    0,    4,    0},
      { 2,    1,   -2,    0,    1},
      { 2,   -1,    0,   -2,    2},
      { 0,    0,    1,   -1,    0},
      {-1,    2,    0,    1,    0},
      {-2,    1,    2,    0,    2},
      { 1,    1,    0,   -1,    1},
      { 1,    0,    1,   -2,    1},
      { 0,    2,    0,    0,    2},
      { 1,   -1,    2,   -3,    1},
      {-1,    1,    2,   -1,    1},
      {-2,    0,    4,   -2,    2},
      {-2,    0,    4,   -2,    1},
      {-2,   -2,    0,    2,    1},
      {-2,    0,   -2,    4,    0},
      { 1,    2,    2,   -4,    1},
      { 1,    1,    2,   -4,    2},
      {-1,    2,    2,   -2,    1},
      { 2,    0,    0,   -3,    1},
      {-1,    2,    0,    0,    1},
      { 0,    0,    0,   -2,    0},
      {-1,   -1,    2,   -2,    2},
      {-1,    1,    0,    0,    2},
      { 0,    0,    0,   -1,    2},
      {-2,    1,    0,    1,    0},
      { 1,   -2,    0,   -2,    1},
      { 1,    0,   -2,    0,    2},
      {-3,    1,    0,    2,    0},
      {-1,    1,   -2,    2,    0},
      {-1,   -1,    0,    0,    2},
      {-3,    0,    0,    2,    0},
      {-3,   -1,    0,    2,    0},
      { 2,    0,    2,   -6,    1},
      { 0,    1,    2,   -4,    2},
      { 2,    0,    0,   -4,    2},
      {-2,    1,    2,   -2,    1},
      { 0,   -1,    2,   -4,    1},
      { 0,    1,    0,   -2,    2},
      {-1,    0,    0,   -2,    0},
      { 2,    0,   -2,   -2,    1},
      {-4,    0,    2,    0,    1},
      {-1,   -1,    0,   -1,    1},
      { 0,    0,   -2,    0,    2},
      {-3,    0,    0,    1,    0},
      {-1,    0,   -2,    1,    0},
      {-2,    0,   -2,    2,    1},
      { 0,    0,   -4,    2,    0},
      {-2,   -1,   -2,    2,    0},
      { 1,    0,    2,   -6,    1},
      {-1,    0,    2,   -4,    2},
      { 1,    0,    0,   -4,    2},
      { 2,    1,    2,   -4,    2},
      { 2,    1,    2,   -4,    1},
      { 0,    1,    4,   -4,    4},
      { 0,    1,    4,   -4,    2},
      {-1,   -1,   -2,    4,    0},
      {-1,   -3,    0,    2,    0},
      {-1,    0,   -2,    4,    1},
      {-2,   -1,    0,    3,    0},
      { 0,    0,   -2,    3,    0},
      {-2,    0,    0,    3,    1},
      { 0,   -1,    0,    1,    0},
      {-3,    0,    2,    2,    0},
      { 1,    1,   -2,    2,    0},
      {-1,    1,    0,    2,    2},
      { 1,   -2,    2,   -2,    1},
      { 0,    0,    1,    0,    2},
      { 0,    0,    1,    0,    1},
      { 0,    0,    1,    0,    0},
      {-1,    2,    0,    2,    1},
      { 0,    0,    2,    0,    2},
      {-2,    0,    2,    0,    2},
      { 2,    0,    0,   -1,    1},
      { 3,    0,    0,   -2,    1},
      { 1,    0,    2,   -2,    3},
      { 1,    2,    0,    0,    1},
      { 2,    0,    2,   -3,    2},
      {-1,    1,    4,   -2,    2},
      {-2,   -2,    0,    4,    0},
      { 0,   -3,    0,    2,    0},
      { 0,    0,   -2,    4,    0},
      {-1,   -1,    0,    3,    0},
      {-2,    0,    0,    4,    2},
      {-1,    0,    0,    3,    1},
      { 2,   -2,    0,    0,    0},
      { 1,   -1,    0,    1,    0},
      {-1,    0,    0,    2,    0},
      { 0,   -2,    2,    0,    1},
      {-1,    0,    1,    2,    1},
      {-1,    1,    0,    3,    0},
      {-1,   -1,    2,    1,    2},
      { 0,   -1,    2,    0,    0},
      {-2,    1,    2,    2,    1},
      { 2,   -2,    2,   -2,    2},
      { 1,    1,    0,    1,    1},
      { 1,    0,    1,    0,    1},
      { 1,    0,    1,    0,    0},
      { 0,    2,    0,    2,    0},
      { 2,   -1,    2,   -2,    1},
      { 0,   -1,    4,   -2,    1},
      { 0,    0,    4,   -2,    3},
      { 0,    1,    4,   -2,    1},
      { 4,    0,    2,   -4,    2},
      { 2,    2,    2,   -2,    2},
      { 2,    0,    4,   -4,    2},
      {-1,   -2,    0,    4,    0},
      {-1,   -3,    2,    2,    2},
      {-3,    0,    2,    4,    2},
      {-3,    0,    2,   -2,    1},
      {-1,   -1,    0,   -2,    1},
      {-3,    0,    0,    0,    2},
      {-3,    0,   -2,    2,    0},
      { 0,    1,    0,   -4,    1},
      {-2,    1,    0,   -2,    1},
      {-4,    0,    0,    0,    1},
      {-1,    0,    0,   -4,    1},
      {-3,    0,    0,   -2,    1},
      { 0,    0,    0,    3,    2},
      {-1,    1,    0,    4,    1},
      { 1,   -2,    2,    0,    1},
      { 0,    1,    0,    3,    0},
      {-1,    0,    2,    2,    3},
      { 0,    0,    2,    2,    2},
      {-2,    0,    2,    2,    2},
      {-1,    1,    2,    2,    0},
      { 3,    0,    0,    0,    2},
      { 2,    1,    0,    1,    0},
      { 2,   -1,    2,   -1,    2},
      { 0,    0,    2,    0,    1},
      { 0,    0,    3,    0,    3},
      { 0,    0,    3,    0,    2},
      {-1,    2,    2,    2,    1},
      {-1,    0,    4,    0,    0},
      { 1,    2,    2,    0,    1},
      { 3,    1,    2,   -2,    1},
      { 1,    1,    4,   -2,    2},
      {-2,   -1,    0,    6,    0},
      { 0,   -2,    0,    4,    0},
      {-2,    0,    0,    6,    1},
      {-2,   -2,    2,    4,    2},
      { 0,   -3,    2,    2,    2},
      { 0,    0,    0,    4,    2},
      {-1,   -1,    2,    3,    2},
      {-2,    0,    2,    4,    0},
      { 2,   -1,    0,    2,    1},
      { 1,    0,    0,    3,    0},
      { 0,    1,    0,    4,    1},
      { 0,    1,    0,    4,    0},
      { 1,   -1,    2,    1,    2},
      { 0,    0,    2,    2,    3},
      { 1,    0,    2,    2,    2},
      {-1,    0,    2,    2,    2},
      {-2,    0,    4,    2,    1},
      { 2,    1,    0,    2,    1},
      { 2,    1,    0,    2,    0},
      { 2,   -1,    2,    0,    0},
      { 1,    0,    2,    1,    0},
      { 0,    1,    2,    2,    0},
      { 2,    0,    2,    0,    3},
      { 3,    0,    2,    0,    2},
      { 1,    0,    2,    0,    2},
      { 1,    0,    3,    0,    3},
      { 1,    1,    2,    1,    1},
      { 0,    2,    2,    2,    2},
      { 2,    1,    2,    0,    0},
      { 2,    0,    4,   -2,    1},
      { 4,    1,    2,   -2,    2},
      {-1,   -1,    0,    6,    0},
      {-3,   -1,    2,    6,    2},
      {-1,    0,    0,    6,    1},
      {-3,    0,    2,    6,    1},
      { 1,   -1,    0,    4,    1},
      { 1,   -1,    0,    4,    0},
      {-2,    0,    2,    5,    2},
      { 1,   -2,    2,    2,    1},
      { 3,   -1,    0,    2,    0},
      { 1,   -1,    2,    2,    0},
      { 0,    0,    2,    3,    1},
      {-1,    1,    2,    4,    1},
      { 0,    1,    2,    3,    2},
      {-1,    0,    4,    2,    1},
      { 2,    0,    2,    1,    1},
      { 5,    0,    0,    0,    0},
      { 2,    1,    2,    1,    2},
      { 1,    0,    4,    0,    1},
      { 3,    1,    2,    0,    1},
      { 3,    0,    4,   -2,    2},
      {-2,   -1,    2,    6,    2},
      { 0,    0,    0,    6,    0},
      { 0,   -2,    2,    4,    2},
      {-2,    0,    2,    6,    1},
      { 2,    0,    0,    4,    1},
      { 2,    0,    0,    4,    0},
      { 2,   -2,    2,    2,    2},
      { 0,    0,    2,    4,    0},
      { 1,    0,    2,    3,    2},
      { 4,    0,    0,    2,    0},
      { 2,    0,    2,    2,    0},
      { 0,    0,    4,    2,    2},
      { 4,   -1,    2,    0,    2},
      { 3,    0,    2,    1,    2},
      { 2,    1,    2,    2,    1},
      { 4,    1,    2,    0,    2},
      {-1,   -1,    2,    6,    2},
      {-1,    0,    2,    6,    1},
      { 1,   -1,    2,    4,    1},
      { 1,    1,    2,    4,    2},
      { 3,    1,    2,    2,    2},
      { 5,    0,    2,    0,    1},
      { 2,   -1,    2,    4,    2},
      { 2,    0,    2,    4,    1}};

/*
   Luni-Solar nutation coefficients, unit 1e-7 arcsec:
   longitude (sin, t*sin, cos), obliquity (cos, t*cos, sin)

   Each row of coefficients in 'cls_t' belongs with the corresponding
   row of fundamental-argument multipliers in 'nals_t'.
*/

   static const double cls_t[678][6] = {
      {-172064161.0, -174666.0,  33386.0, 92052331.0,  9086.0, 15377.0},
      { -13170906.0,   -1675.0, -13696.0,  5730336.0, -3015.0, -4587.0},
      {  -2276413.0,    -234.0,   2796.0,   978459.0,  -485.0,  1374.0},
      {   2074554.0,     207.0,   -698.0,  -897492.0,   470.0,  -291.0},
      {   1475877.0,   -3633.0,  11817.0,    73871.0,  -184.0, -1924.0},
      {   -516821.0,    1226.0,   -524.0,   224386.0,  -677.0,  -174.0},
      {    711159.0,      73.0,   -872.0,    -6750.0,     0.0,   358.0},
      {   -387298.0,    -367.0,    380.0,   200728.0,    18.0,   318.0},
      {   -301461.0,     -36.0,    816.0,   129025.0,   -63.0,   367.0},
      {    215829.0,    -494.0,    111.0,   -95929.0,   299.0,   132.0},
      {    128227.0,     137.0,    181.0,   -68982.0,    -9.0,    39.0},
      {    123457.0,      11.0,     19.0,   -53311.0,    32.0,    -4.0},
      {    156994.0,      10.0,   -168.0,    -1235.0,     0.0,    82.0},
      {     63110.0,      63.0,     27.0,   -33228.0,     0.0,    -9.0},
      {    -57976.0,     -63.0,   -189.0,    31429.0,     0.0,   -75.0},
      {    -59641.0,     -11.0,    149.0,    25543.0,   -11.0,    66.0},
      {    -51613.0,     -42.0,    129.0,    26366.0,     0.0,    78.0},
      {     45893.0,      50.0,     31.0,   -24236.0,   -10.0,    20.0},
      {     63384.0,      11.0,   -150.0,    -1220.0,     0.0,    29.0},
      {    -38571.0,      -1.0,    158.0,    16452.0,   -11.0,    68.0},
      {     32481.0,       0.0,      0.0,   -13870.0,     0.0,     0.0},
      {    -47722.0,       0.0,    -18.0,      477.0,     0.0,   -25.0},
      {    -31046.0,      -1.0,    131.0,    13238.0,   -11.0,    59.0},
      {     28593.0,       0.0,     -1.0,   -12338.0,    10.0,    -3.0},
      {     20441.0,      21.0,     10.0,   -10758.0,     0.0,    -3.0},
      {     29243.0,       0.0,    -74.0,     -609.0,     0.0,    13.0},
      {     25887.0,       0.0,    -66.0,     -550.0,     0.0,    11.0},
      {    -14053.0,     -25.0,     79.0,     8551.0,    -2.0,   -45.0},
      {     15164.0,      10.0,     11.0,    -8001.0,     0.0,    -1.0},
      {    -15794.0,      72.0,    -16.0,     6850.0,   -42.0,    -5.0},
      {     21783.0,       0.0,     13.0,     -167.0,     0.0,    13.0},
      {    -12873.0,     -10.0,    -37.0,     6953.0,     0.0,   -14.0},
      {    -12654.0,      11.0,     63.0,     6415.0,     0.0,    26.0},
      {    -10204.0,       0.0,     25.0,     5222.0,     0.0,    15.0},
      {     16707.0,     -85.0,    -10.0,      168.0,    -1.0,    10.0},
      {     -7691.0,       0.0,     44.0,     3268.0,     0.0,    19.0},
      {    -11024.0,       0.0,    -14.0,      104.0,     0.0,     2.0},
      {      7566.0,     -21.0,    -11.0,    -3250.0,     0.0,    -5.0},
      {     -6637.0,     -11.0,     25.0,     3353.0,     0.0,    14.0},
      {     -7141.0,      21.0,      8.0,     3070.0,     0.0,     4.0},
      {     -6302.0,     -11.0,      2.0,     3272.0,     0.0,     4.0},
      {      5800.0,      10.0,      2.0,    -3045.0,     0.0,    -1.0},
      {      6443.0,       0.0,     -7.0,    -2768.0,     0.0,    -4.0},
      {     -5774.0,     -11.0,    -15.0,     3041.0,     0.0,    -5.0},
      {     -5350.0,       0.0,     21.0,     2695.0,     0.0,    12.0},
      {     -4752.0,     -11.0,     -3.0,     2719.0,     0.0,    -3.0},
      {     -4940.0,     -11.0,    -21.0,     2720.0,     0.0,    -9.0},
      {      7350.0,       0.0,     -8.0,      -51.0,     0.0,     4.0},
      {      4065.0,       0.0,      6.0,    -2206.0,     0.0,     1.0},
      {      6579.0,       0.0,    -24.0,     -199.0,     0.0,     2.0},
      {      3579.0,       0.0,      5.0,    -1900.0,     0.0,     1.0},
      {      4725.0,       0.0,     -6.0,      -41.0,     0.0,     3.0},
      {     -3075.0,       0.0,     -2.0,     1313.0,     0.0,    -1.0},
      {     -2904.0,       0.0,     15.0,     1233.0,     0.0,     7.0},
      {      4348.0,       0.0,    -10.0,      -81.0,     0.0,     2.0},
      {     -2878.0,       0.0,      8.0,     1232.0,     0.0,     4.0},
      {     -4230.0,       0.0,      5.0,      -20.0,     0.0,    -2.0},
      {     -2819.0,       0.0,      7.0,     1207.0,     0.0,     3.0},
      {     -4056.0,       0.0,      5.0,       40.0,     0.0,    -2.0},
      {     -2647.0,       0.0,     11.0,     1129.0,     0.0,     5.0},
      {     -2294.0,       0.0,    -10.0,     1266.0,     0.0,    -4.0},
      {      2481.0,       0.0,     -7.0,    -1062.0,     0.0,    -3.0},
      {      2179.0,       0.0,     -2.0,    -1129.0,     0.0,    -2.0},
      {      3276.0,       0.0,      1.0,       -9.0,     0.0,     0.0},
      {     -3389.0,       0.0,      5.0,       35.0,     0.0,    -2.0},
      {      3339.0,       0.0,    -13.0,     -107.0,     0.0,     1.0},
      {     -1987.0,       0.0,     -6.0,     1073.0,     0.0,    -2.0},
      {     -1981.0,       0.0,      0.0,      854.0,     0.0,     0.0},
      {      4026.0,       0.0,   -353.0,     -553.0,     0.0,  -139.0},
      {      1660.0,       0.0,     -5.0,     -710.0,     0.0,    -2.0},
      {     -1521.0,       0.0,      9.0,      647.0,     0.0,     4.0},
      {      1314.0,       0.0,      0.0,     -700.0,     0.0,     0.0},
      {     -1283.0,       0.0,      0.0,      672.0,     0.0,     0.0},
      {     -1331.0,       0.0,      8.0,      663.0,     0.0,     4.0},
      {      1383.0,       0.0,     -2.0,     -594.0,     0.0,    -2.0},
      {      1405.0,       0.0,      4.0,     -610.0,     0.0,     2.0},
      {      1290.0,       0.0,      0.0,     -556.0,     0.0,     0.0},
      {     -1214.0,       0.0,      5.0,      518.0,     0.0,     2.0},
      {      1146.0,       0.0,     -3.0,     -490.0,     0.0,    -1.0},
      {      1019.0,       0.0,     -1.0,     -527.0,     0.0,    -1.0},
      {     -1100.0,       0.0,      9.0,      465.0,     0.0,     4.0},
      {      -970.0,       0.0,      2.0,      496.0,     0.0,     1.0},
      {      1575.0,       0.0,     -6.0,      -50.0,     0.0,     0.0},
      {       934.0,       0.0,     -3.0,     -399.0,     0.0,    -1.0},
      {       922.0,       0.0,     -1.0,     -395.0,     0.0,    -1.0},
      {       815.0,       0.0,     -1.0,     -422.0,     0.0,    -1.0},
      {       834.0,       0.0,      2.0,     -440.0,     0.0,     1.0},
      {      1248.0,       0.0,      0.0,     -170.0,     0.0,     1.0},
      {      1338.0,       0.0,     -5.0,      -39.0,     0.0,     0.0},
      {       716.0,       0.0,     -2.0,     -389.0,     0.0,    -1.0},
      {      1282.0,       0.0,     -3.0,      -23.0,     0.0,     1.0},
      {       742.0,       0.0,      1.0,     -391.0,     0.0,     0.0},
      {      1020.0,       0.0,    -25.0,     -495.0,     0.0,   -10.0},
      {       715.0,       0.0,     -4.0,     -326.0,     0.0,     2.0},
      {      -666.0,       0.0,     -3.0,      369.0,     0.0,    -1.0},
      {      -667.0,       0.0,      1.0,      346.0,     0.0,     1.0},
      {      -704.0,       0.0,      0.0,      304.0,     0.0,     0.0},
      {      -694.0,       0.0,      5.0,      294.0,     0.0,     2.0},
      {     -1014.0,       0.0,     -1.0,        4.0,     0.0,    -1.0},
      {      -585.0,       0.0,     -2.0,      316.0,     0.0,    -1.0},
      {      -949.0,       0.0,      1.0,        8.0,     0.0,    -1.0},
      {      -595.0,       0.0,      0.0,      258.0,     0.0,     0.0},
      {       528.0,       0.0,      0.0,     -279.0,     0.0,     0.0},
      {      -590.0,       0.0,      4.0,      252.0,     0.0,     2.0},
      {       570.0,       0.0,     -2.0,     -244.0,     0.0,    -1.0},
      {      -502.0,       0.0,      3.0,      250.0,     0.0,     2.0},
      {      -875.0,       0.0,      1.0,       29.0,     0.0,     0.0},
      {      -492.0,       0.0,     -3.0,      275.0,     0.0,    -1.0},
      {       535.0,       0.0,     -2.0,     -228.0,     0.0,    -1.0},
      {      -467.0,       0.0,      1.0,      240.0,     0.0,     1.0},
      {       591.0,       0.0,      0.0,     -253.0,     0.0,     0.0},
      {      -453.0,       0.0,     -1.0,      244.0,     0.0,    -1.0},
      {       766.0,       0.0,      1.0,        9.0,     0.0,     0.0},
      {      -446.0,       0.0,      2.0,      225.0,     0.0,     1.0},
      {      -488.0,       0.0,      2.0,      207.0,     0.0,     1.0},
      {      -468.0,       0.0,      0.0,      201.0,     0.0,     0.0},
      {      -421.0,       0.0,      1.0,      216.0,     0.0,     1.0},
      {       463.0,       0.0,      0.0,     -200.0,     0.0,     0.0},
      {      -673.0,       0.0,      2.0,       14.0,     0.0,     0.0},
      {       658.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {      -438.0,       0.0,      0.0,      188.0,     0.0,     0.0},
      {      -390.0,       0.0,      0.0,      205.0,     0.0,     0.0},
      {       639.0,     -11.0,     -2.0,      -19.0,     0.0,     0.0},
      {       412.0,       0.0,     -2.0,     -176.0,     0.0,    -1.0},
      {      -361.0,       0.0,      0.0,      189.0,     0.0,     0.0},
      {       360.0,       0.0,     -1.0,     -185.0,     0.0,    -1.0},
      {       588.0,       0.0,     -3.0,      -24.0,     0.0,     0.0},
      {      -578.0,       0.0,      1.0,        5.0,     0.0,     0.0},
      {      -396.0,       0.0,      0.0,      171.0,     0.0,     0.0},
      {       565.0,       0.0,     -1.0,       -6.0,     0.0,     0.0},
      {      -335.0,       0.0,     -1.0,      184.0,     0.0,    -1.0},
      {       357.0,       0.0,      1.0,     -154.0,     0.0,     0.0},
      {       321.0,       0.0,      1.0,     -174.0,     0.0,     0.0},
      {      -301.0,       0.0,     -1.0,      162.0,     0.0,     0.0},
      {      -334.0,       0.0,      0.0,      144.0,     0.0,     0.0},
      {       493.0,       0.0,     -2.0,      -15.0,     0.0,     0.0},
      {       494.0,       0.0,     -2.0,      -19.0,     0.0,     0.0},
      {       337.0,       0.0,     -1.0,     -143.0,     0.0,    -1.0},
      {       280.0,       0.0,     -1.0,     -144.0,     0.0,     0.0},
      {       309.0,       0.0,      1.0,     -134.0,     0.0,     0.0},
      {      -263.0,       0.0,      2.0,      131.0,     0.0,     1.0},
      {       253.0,       0.0,      1.0,     -138.0,     0.0,     0.0},
      {       245.0,       0.0,      0.0,     -128.0,     0.0,     0.0},
      {       416.0,       0.0,     -2.0,      -17.0,     0.0,     0.0},
      {      -229.0,       0.0,      0.0,      128.0,     0.0,     0.0},
      {       231.0,       0.0,      0.0,     -120.0,     0.0,     0.0},
      {      -259.0,       0.0,      2.0,      109.0,     0.0,     1.0},
      {       375.0,       0.0,     -1.0,       -8.0,     0.0,     0.0},
      {       252.0,       0.0,      0.0,     -108.0,     0.0,     0.0},
      {      -245.0,       0.0,      1.0,      104.0,     0.0,     0.0},
      {       243.0,       0.0,     -1.0,     -104.0,     0.0,     0.0},
      {       208.0,       0.0,      1.0,     -112.0,     0.0,     0.0},
      {       199.0,       0.0,      0.0,     -102.0,     0.0,     0.0},
      {      -208.0,       0.0,      1.0,      105.0,     0.0,     0.0},
      {       335.0,       0.0,     -2.0,      -14.0,     0.0,     0.0},
      {      -325.0,       0.0,      1.0,        7.0,     0.0,     0.0},
      {      -187.0,       0.0,      0.0,       96.0,     0.0,     0.0},
      {       197.0,       0.0,     -1.0,     -100.0,     0.0,     0.0},
      {      -192.0,       0.0,      2.0,       94.0,     0.0,     1.0},
      {      -188.0,       0.0,      0.0,       83.0,     0.0,     0.0},
      {       276.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {      -286.0,       0.0,      1.0,        6.0,     0.0,     0.0},
      {       186.0,       0.0,     -1.0,      -79.0,     0.0,     0.0},
      {      -219.0,       0.0,      0.0,       43.0,     0.0,     0.0},
      {       276.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {      -153.0,       0.0,     -1.0,       84.0,     0.0,     0.0},
      {      -156.0,       0.0,      0.0,       81.0,     0.0,     0.0},
      {      -154.0,       0.0,      1.0,       78.0,     0.0,     0.0},
      {      -174.0,       0.0,      1.0,       75.0,     0.0,     0.0},
      {      -163.0,       0.0,      2.0,       69.0,     0.0,     1.0},
      {      -228.0,       0.0,      0.0,        1.0,     0.0,     0.0},
      {        91.0,       0.0,     -4.0,      -54.0,     0.0,    -2.0},
      {       175.0,       0.0,      0.0,      -75.0,     0.0,     0.0},
      {      -159.0,       0.0,      0.0,       69.0,     0.0,     0.0},
      {       141.0,       0.0,      0.0,      -72.0,     0.0,     0.0},
      {       147.0,       0.0,      0.0,      -75.0,     0.0,     0.0},
      {      -132.0,       0.0,      0.0,       69.0,     0.0,     0.0},
      {       159.0,       0.0,    -28.0,      -54.0,     0.0,    11.0},
      {       213.0,       0.0,      0.0,       -4.0,     0.0,     0.0},
      {       123.0,       0.0,      0.0,      -64.0,     0.0,     0.0},
      {      -118.0,       0.0,     -1.0,       66.0,     0.0,     0.0},
      {       144.0,       0.0,     -1.0,      -61.0,     0.0,     0.0},
      {      -121.0,       0.0,      1.0,       60.0,     0.0,     0.0},
      {      -134.0,       0.0,      1.0,       56.0,     0.0,     1.0},
      {      -105.0,       0.0,      0.0,       57.0,     0.0,     0.0},
      {      -102.0,       0.0,      0.0,       56.0,     0.0,     0.0},
      {       120.0,       0.0,      0.0,      -52.0,     0.0,     0.0},
      {       101.0,       0.0,      0.0,      -54.0,     0.0,     0.0},
      {      -113.0,       0.0,      0.0,       59.0,     0.0,     0.0},
      {      -106.0,       0.0,      0.0,       61.0,     0.0,     0.0},
      {      -129.0,       0.0,      1.0,       55.0,     0.0,     0.0},
      {      -114.0,       0.0,      0.0,       57.0,     0.0,     0.0},
      {       113.0,       0.0,     -1.0,      -49.0,     0.0,     0.0},
      {      -102.0,       0.0,      0.0,       44.0,     0.0,     0.0},
      {       -94.0,       0.0,      0.0,       51.0,     0.0,     0.0},
      {      -100.0,       0.0,     -1.0,       56.0,     0.0,     0.0},
      {        87.0,       0.0,      0.0,      -47.0,     0.0,     0.0},
      {       161.0,       0.0,      0.0,       -1.0,     0.0,     0.0},
      {        96.0,       0.0,      0.0,      -50.0,     0.0,     0.0},
      {       151.0,       0.0,     -1.0,       -5.0,     0.0,     0.0},
      {      -104.0,       0.0,      0.0,       44.0,     0.0,     0.0},
      {      -110.0,       0.0,      0.0,       48.0,     0.0,     0.0},
      {      -100.0,       0.0,      1.0,       50.0,     0.0,     0.0},
      {        92.0,       0.0,     -5.0,       12.0,     0.0,    -2.0},
      {        82.0,       0.0,      0.0,      -45.0,     0.0,     0.0},
      {        82.0,       0.0,      0.0,      -45.0,     0.0,     0.0},
      {       -78.0,       0.0,      0.0,       41.0,     0.0,     0.0},
      {       -77.0,       0.0,      0.0,       43.0,     0.0,     0.0},
      {         2.0,       0.0,      0.0,       54.0,     0.0,     0.0},
      {        94.0,       0.0,      0.0,      -40.0,     0.0,     0.0},
      {       -93.0,       0.0,      0.0,       40.0,     0.0,     0.0},
      {       -83.0,       0.0,     10.0,       40.0,     0.0,    -2.0},
      {        83.0,       0.0,      0.0,      -36.0,     0.0,     0.0},
      {       -91.0,       0.0,      0.0,       39.0,     0.0,     0.0},
      {       128.0,       0.0,      0.0,       -1.0,     0.0,     0.0},
      {       -79.0,       0.0,      0.0,       34.0,     0.0,     0.0},
      {       -83.0,       0.0,      0.0,       47.0,     0.0,     0.0},
      {        84.0,       0.0,      0.0,      -44.0,     0.0,     0.0},
      {        83.0,       0.0,      0.0,      -43.0,     0.0,     0.0},
      {        91.0,       0.0,      0.0,      -39.0,     0.0,     0.0},
      {       -77.0,       0.0,      0.0,       39.0,     0.0,     0.0},
      {        84.0,       0.0,      0.0,      -43.0,     0.0,     0.0},
      {       -92.0,       0.0,      1.0,       39.0,     0.0,     0.0},
      {       -92.0,       0.0,      1.0,       39.0,     0.0,     0.0},
      {       -94.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        68.0,       0.0,      0.0,      -36.0,     0.0,     0.0},
      {       -61.0,       0.0,      0.0,       32.0,     0.0,     0.0},
      {        71.0,       0.0,      0.0,      -31.0,     0.0,     0.0},
      {        62.0,       0.0,      0.0,      -34.0,     0.0,     0.0},
      {       -63.0,       0.0,      0.0,       33.0,     0.0,     0.0},
      {       -73.0,       0.0,      0.0,       32.0,     0.0,     0.0},
      {       115.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {      -103.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {        63.0,       0.0,      0.0,      -28.0,     0.0,     0.0},
      {        74.0,       0.0,      0.0,      -32.0,     0.0,     0.0},
      {      -103.0,       0.0,     -3.0,        3.0,     0.0,    -1.0},
      {       -69.0,       0.0,      0.0,       30.0,     0.0,     0.0},
      {        57.0,       0.0,      0.0,      -29.0,     0.0,     0.0},
      {        94.0,       0.0,      0.0,       -4.0,     0.0,     0.0},
      {        64.0,       0.0,      0.0,      -33.0,     0.0,     0.0},
      {       -63.0,       0.0,      0.0,       26.0,     0.0,     0.0},
      {       -38.0,       0.0,      0.0,       20.0,     0.0,     0.0},
      {       -43.0,       0.0,      0.0,       24.0,     0.0,     0.0},
      {       -45.0,       0.0,      0.0,       23.0,     0.0,     0.0},
      {        47.0,       0.0,      0.0,      -24.0,     0.0,     0.0},
      {       -48.0,       0.0,      0.0,       25.0,     0.0,     0.0},
      {        45.0,       0.0,      0.0,      -26.0,     0.0,     0.0},
      {        56.0,       0.0,      0.0,      -25.0,     0.0,     0.0},
      {        88.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {       -75.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        85.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        49.0,       0.0,      0.0,      -26.0,     0.0,     0.0},
      {       -74.0,       0.0,     -3.0,       -1.0,     0.0,    -1.0},
      {       -39.0,       0.0,      0.0,       21.0,     0.0,     0.0},
      {        45.0,       0.0,      0.0,      -20.0,     0.0,     0.0},
      {        51.0,       0.0,      0.0,      -22.0,     0.0,     0.0},
      {       -40.0,       0.0,      0.0,       21.0,     0.0,     0.0},
      {        41.0,       0.0,      0.0,      -21.0,     0.0,     0.0},
      {       -42.0,       0.0,      0.0,       24.0,     0.0,     0.0},
      {       -51.0,       0.0,      0.0,       22.0,     0.0,     0.0},
      {       -42.0,       0.0,      0.0,       22.0,     0.0,     0.0},
      {        39.0,       0.0,      0.0,      -21.0,     0.0,     0.0},
      {        46.0,       0.0,      0.0,      -18.0,     0.0,     0.0},
      {       -53.0,       0.0,      0.0,       22.0,     0.0,     0.0},
      {        82.0,       0.0,      0.0,       -4.0,     0.0,     0.0},
      {        81.0,       0.0,     -1.0,       -4.0,     0.0,     0.0},
      {        47.0,       0.0,      0.0,      -19.0,     0.0,     0.0},
      {        53.0,       0.0,      0.0,      -23.0,     0.0,     0.0},
      {       -45.0,       0.0,      0.0,       22.0,     0.0,     0.0},
      {       -44.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {       -33.0,       0.0,      0.0,       16.0,     0.0,     0.0},
      {       -61.0,       0.0,      0.0,        1.0,     0.0,     0.0},
      {        28.0,       0.0,      0.0,      -15.0,     0.0,     0.0},
      {       -38.0,       0.0,      0.0,       19.0,     0.0,     0.0},
      {       -33.0,       0.0,      0.0,       21.0,     0.0,     0.0},
      {       -60.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        48.0,       0.0,      0.0,      -10.0,     0.0,     0.0},
      {        27.0,       0.0,      0.0,      -14.0,     0.0,     0.0},
      {        38.0,       0.0,      0.0,      -20.0,     0.0,     0.0},
      {        31.0,       0.0,      0.0,      -13.0,     0.0,     0.0},
      {       -29.0,       0.0,      0.0,       15.0,     0.0,     0.0},
      {        28.0,       0.0,      0.0,      -15.0,     0.0,     0.0},
      {       -32.0,       0.0,      0.0,       15.0,     0.0,     0.0},
      {        45.0,       0.0,      0.0,       -8.0,     0.0,     0.0},
      {       -44.0,       0.0,      0.0,       19.0,     0.0,     0.0},
      {        28.0,       0.0,      0.0,      -15.0,     0.0,     0.0},
      {       -51.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {       -36.0,       0.0,      0.0,       20.0,     0.0,     0.0},
      {        44.0,       0.0,      0.0,      -19.0,     0.0,     0.0},
      {        26.0,       0.0,      0.0,      -14.0,     0.0,     0.0},
      {       -60.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {        35.0,       0.0,      0.0,      -18.0,     0.0,     0.0},
      {       -27.0,       0.0,      0.0,       11.0,     0.0,     0.0},
      {        47.0,       0.0,      0.0,       -1.0,     0.0,     0.0},
      {        36.0,       0.0,      0.0,      -15.0,     0.0,     0.0},
      {       -36.0,       0.0,      0.0,       20.0,     0.0,     0.0},
      {       -35.0,       0.0,      0.0,       19.0,     0.0,     0.0},
      {       -37.0,       0.0,      0.0,       19.0,     0.0,     0.0},
      {        32.0,       0.0,      0.0,      -16.0,     0.0,     0.0},
      {        35.0,       0.0,      0.0,      -14.0,     0.0,     0.0},
      {        32.0,       0.0,      0.0,      -13.0,     0.0,     0.0},
      {        65.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {        47.0,       0.0,      0.0,       -1.0,     0.0,     0.0},
      {        32.0,       0.0,      0.0,      -16.0,     0.0,     0.0},
      {        37.0,       0.0,      0.0,      -16.0,     0.0,     0.0},
      {       -30.0,       0.0,      0.0,       15.0,     0.0,     0.0},
      {       -32.0,       0.0,      0.0,       16.0,     0.0,     0.0},
      {       -31.0,       0.0,      0.0,       13.0,     0.0,     0.0},
      {        37.0,       0.0,      0.0,      -16.0,     0.0,     0.0},
      {        31.0,       0.0,      0.0,      -13.0,     0.0,     0.0},
      {        49.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {        32.0,       0.0,      0.0,      -13.0,     0.0,     0.0},
      {        23.0,       0.0,      0.0,      -12.0,     0.0,     0.0},
      {       -43.0,       0.0,      0.0,       18.0,     0.0,     0.0},
      {        26.0,       0.0,      0.0,      -11.0,     0.0,     0.0},
      {       -32.0,       0.0,      0.0,       14.0,     0.0,     0.0},
      {       -29.0,       0.0,      0.0,       14.0,     0.0,     0.0},
      {       -27.0,       0.0,      0.0,       12.0,     0.0,     0.0},
      {        30.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {       -11.0,       0.0,      0.0,        5.0,     0.0,     0.0},
      {       -21.0,       0.0,      0.0,       10.0,     0.0,     0.0},
      {       -34.0,       0.0,      0.0,       15.0,     0.0,     0.0},
      {       -10.0,       0.0,      0.0,        6.0,     0.0,     0.0},
      {       -36.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -9.0,       0.0,      0.0,        4.0,     0.0,     0.0},
      {       -12.0,       0.0,      0.0,        5.0,     0.0,     0.0},
      {       -21.0,       0.0,      0.0,        5.0,     0.0,     0.0},
      {       -29.0,       0.0,      0.0,       -1.0,     0.0,     0.0},
      {       -15.0,       0.0,      0.0,        3.0,     0.0,     0.0},
      {       -20.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        28.0,       0.0,      0.0,        0.0,     0.0,    -2.0},
      {        17.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {       -22.0,       0.0,      0.0,       12.0,     0.0,     0.0},
      {       -14.0,       0.0,      0.0,        7.0,     0.0,     0.0},
      {        24.0,       0.0,      0.0,      -11.0,     0.0,     0.0},
      {        11.0,       0.0,      0.0,       -6.0,     0.0,     0.0},
      {        14.0,       0.0,      0.0,       -6.0,     0.0,     0.0},
      {        24.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        18.0,       0.0,      0.0,       -8.0,     0.0,     0.0},
      {       -38.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {       -31.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {       -16.0,       0.0,      0.0,        8.0,     0.0,     0.0},
      {        29.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {       -18.0,       0.0,      0.0,       10.0,     0.0,     0.0},
      {       -10.0,       0.0,      0.0,        5.0,     0.0,     0.0},
      {       -17.0,       0.0,      0.0,       10.0,     0.0,     0.0},
      {         9.0,       0.0,      0.0,       -4.0,     0.0,     0.0},
      {        16.0,       0.0,      0.0,       -6.0,     0.0,     0.0},
      {        22.0,       0.0,      0.0,      -12.0,     0.0,     0.0},
      {        20.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {       -13.0,       0.0,      0.0,        6.0,     0.0,     0.0},
      {       -17.0,       0.0,      0.0,        9.0,     0.0,     0.0},
      {       -14.0,       0.0,      0.0,        8.0,     0.0,     0.0},
      {         0.0,       0.0,      0.0,       -7.0,     0.0,     0.0},
      {        14.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        19.0,       0.0,      0.0,      -10.0,     0.0,     0.0},
      {       -34.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {       -20.0,       0.0,      0.0,        8.0,     0.0,     0.0},
      {         9.0,       0.0,      0.0,       -5.0,     0.0,     0.0},
      {       -18.0,       0.0,      0.0,        7.0,     0.0,     0.0},
      {        13.0,       0.0,      0.0,       -6.0,     0.0,     0.0},
      {        17.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {       -12.0,       0.0,      0.0,        5.0,     0.0,     0.0},
      {        15.0,       0.0,      0.0,       -8.0,     0.0,     0.0},
      {       -11.0,       0.0,      0.0,        3.0,     0.0,     0.0},
      {        13.0,       0.0,      0.0,       -5.0,     0.0,     0.0},
      {       -18.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {       -35.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         9.0,       0.0,      0.0,       -4.0,     0.0,     0.0},
      {       -19.0,       0.0,      0.0,       10.0,     0.0,     0.0},
      {       -26.0,       0.0,      0.0,       11.0,     0.0,     0.0},
      {         8.0,       0.0,      0.0,       -4.0,     0.0,     0.0},
      {       -10.0,       0.0,      0.0,        4.0,     0.0,     0.0},
      {        10.0,       0.0,      0.0,       -6.0,     0.0,     0.0},
      {       -21.0,       0.0,      0.0,        9.0,     0.0,     0.0},
      {       -15.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         9.0,       0.0,      0.0,       -5.0,     0.0,     0.0},
      {       -29.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {       -19.0,       0.0,      0.0,       10.0,     0.0,     0.0},
      {        12.0,       0.0,      0.0,       -5.0,     0.0,     0.0},
      {        22.0,       0.0,      0.0,       -9.0,     0.0,     0.0},
      {       -10.0,       0.0,      0.0,        5.0,     0.0,     0.0},
      {       -20.0,       0.0,      0.0,       11.0,     0.0,     0.0},
      {       -20.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {       -17.0,       0.0,      0.0,        7.0,     0.0,     0.0},
      {        15.0,       0.0,      0.0,       -3.0,     0.0,     0.0},
      {         8.0,       0.0,      0.0,       -4.0,     0.0,     0.0},
      {        14.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {       -12.0,       0.0,      0.0,        6.0,     0.0,     0.0},
      {        25.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {       -13.0,       0.0,      0.0,        6.0,     0.0,     0.0},
      {       -14.0,       0.0,      0.0,        8.0,     0.0,     0.0},
      {        13.0,       0.0,      0.0,       -5.0,     0.0,     0.0},
      {       -17.0,       0.0,      0.0,        9.0,     0.0,     0.0},
      {       -12.0,       0.0,      0.0,        6.0,     0.0,     0.0},
      {       -10.0,       0.0,      0.0,        5.0,     0.0,     0.0},
      {        10.0,       0.0,      0.0,       -6.0,     0.0,     0.0},
      {       -15.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {       -22.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        28.0,       0.0,      0.0,       -1.0,     0.0,     0.0},
      {        15.0,       0.0,      0.0,       -7.0,     0.0,     0.0},
      {        23.0,       0.0,      0.0,      -10.0,     0.0,     0.0},
      {        12.0,       0.0,      0.0,       -5.0,     0.0,     0.0},
      {        29.0,       0.0,      0.0,       -1.0,     0.0,     0.0},
      {       -25.0,       0.0,      0.0,        1.0,     0.0,     0.0},
      {        22.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {       -18.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        15.0,       0.0,      0.0,        3.0,     0.0,     0.0},
      {       -23.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        12.0,       0.0,      0.0,       -5.0,     0.0,     0.0},
      {        -8.0,       0.0,      0.0,        4.0,     0.0,     0.0},
      {       -19.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {       -10.0,       0.0,      0.0,        4.0,     0.0,     0.0},
      {        21.0,       0.0,      0.0,       -9.0,     0.0,     0.0},
      {        23.0,       0.0,      0.0,       -1.0,     0.0,     0.0},
      {       -16.0,       0.0,      0.0,        8.0,     0.0,     0.0},
      {       -19.0,       0.0,      0.0,        9.0,     0.0,     0.0},
      {       -22.0,       0.0,      0.0,       10.0,     0.0,     0.0},
      {        27.0,       0.0,      0.0,       -1.0,     0.0,     0.0},
      {        16.0,       0.0,      0.0,       -8.0,     0.0,     0.0},
      {        19.0,       0.0,      0.0,       -8.0,     0.0,     0.0},
      {         9.0,       0.0,      0.0,       -4.0,     0.0,     0.0},
      {        -9.0,       0.0,      0.0,        4.0,     0.0,     0.0},
      {        -9.0,       0.0,      0.0,        4.0,     0.0,     0.0},
      {        -8.0,       0.0,      0.0,        4.0,     0.0,     0.0},
      {        18.0,       0.0,      0.0,       -9.0,     0.0,     0.0},
      {        16.0,       0.0,      0.0,       -1.0,     0.0,     0.0},
      {       -10.0,       0.0,      0.0,        4.0,     0.0,     0.0},
      {       -23.0,       0.0,      0.0,        9.0,     0.0,     0.0},
      {        16.0,       0.0,      0.0,       -1.0,     0.0,     0.0},
      {       -12.0,       0.0,      0.0,        6.0,     0.0,     0.0},
      {        -8.0,       0.0,      0.0,        4.0,     0.0,     0.0},
      {        30.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {        24.0,       0.0,      0.0,      -10.0,     0.0,     0.0},
      {        10.0,       0.0,      0.0,       -4.0,     0.0,     0.0},
      {       -16.0,       0.0,      0.0,        7.0,     0.0,     0.0},
      {       -16.0,       0.0,      0.0,        7.0,     0.0,     0.0},
      {        17.0,       0.0,      0.0,       -7.0,     0.0,     0.0},
      {       -24.0,       0.0,      0.0,       10.0,     0.0,     0.0},
      {       -12.0,       0.0,      0.0,        5.0,     0.0,     0.0},
      {       -24.0,       0.0,      0.0,       11.0,     0.0,     0.0},
      {       -23.0,       0.0,      0.0,        9.0,     0.0,     0.0},
      {       -13.0,       0.0,      0.0,        5.0,     0.0,     0.0},
      {       -15.0,       0.0,      0.0,        7.0,     0.0,     0.0},
      {         0.0,       0.0,  -1988.0,        0.0,     0.0, -1679.0},
      {         0.0,       0.0,    -63.0,        0.0,     0.0,   -27.0},
      {        -4.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         0.0,       0.0,      5.0,        0.0,     0.0,     4.0},
      {         5.0,       0.0,      0.0,       -3.0,     0.0,     0.0},
      {         0.0,       0.0,    364.0,        0.0,     0.0,   176.0},
      {         0.0,       0.0,  -1044.0,        0.0,     0.0,  -891.0},
      {        -3.0,       0.0,      0.0,        1.0,     0.0,     0.0},
      {         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {         0.0,       0.0,    330.0,        0.0,     0.0,     0.0},
      {         5.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {        -3.0,       0.0,      0.0,        1.0,     0.0,     0.0},
      {        -5.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,       -1.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         0.0,       0.0,      5.0,        0.0,     0.0,     0.0},
      {         0.0,       0.0,      0.0,        1.0,     0.0,     0.0},
      {         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {         6.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         5.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {        -7.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {       -12.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         5.0,       0.0,      0.0,       -3.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,       -1.0,     0.0,     0.0},
      {        -5.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -7.0,       0.0,      0.0,        3.0,     0.0,     0.0},
      {         7.0,       0.0,      0.0,       -4.0,     0.0,     0.0},
      {         0.0,       0.0,    -12.0,        0.0,     0.0,   -10.0},
      {         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {        -3.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {        -7.0,       0.0,      0.0,        3.0,     0.0,     0.0},
      {        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {        -3.0,       0.0,      0.0,        1.0,     0.0,     0.0},
      {         0.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -3.0,       0.0,      0.0,        1.0,     0.0,     0.0},
      {         7.0,       0.0,      0.0,       -3.0,     0.0,     0.0},
      {        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {        -5.0,       0.0,      0.0,        3.0,     0.0,     0.0},
      {         5.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -5.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {         5.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {        -8.0,       0.0,      0.0,        3.0,     0.0,     0.0},
      {         9.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         6.0,       0.0,      0.0,       -3.0,     0.0,     0.0},
      {        -5.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -7.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -3.0,       0.0,      0.0,        1.0,     0.0,     0.0},
      {         5.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -3.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,       -1.0,     0.0,     0.0},
      {        -5.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {         9.0,       0.0,      0.0,       -3.0,     0.0,     0.0},
      {         4.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {        -3.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {         9.0,       0.0,      0.0,       -3.0,     0.0,     0.0},
      {        -4.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -4.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {         8.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -3.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,       -1.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,       -1.0,     0.0,     0.0},
      {        -3.0,       0.0,      0.0,        1.0,     0.0,     0.0},
      {         6.0,       0.0,      0.0,       -3.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -3.0,       0.0,      0.0,        1.0,     0.0,     0.0},
      {        -7.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         9.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -3.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {        -3.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -4.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -5.0,       0.0,      0.0,        3.0,     0.0,     0.0},
      {       -13.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -7.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        10.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,       -1.0,     0.0,     0.0},
      {        10.0,       0.0,     13.0,        6.0,     0.0,    -5.0},
      {         0.0,       0.0,     30.0,        0.0,     0.0,    14.0},
      {         0.0,       0.0,   -162.0,        0.0,     0.0,  -138.0},
      {         0.0,       0.0,     75.0,        0.0,     0.0,     0.0},
      {        -7.0,       0.0,      0.0,        4.0,     0.0,     0.0},
      {        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {         5.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {         5.0,       0.0,      0.0,       -3.0,     0.0,     0.0},
      {        -3.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -3.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {        -5.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {         6.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         9.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         5.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -7.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -3.0,       0.0,      0.0,        1.0,     0.0,     0.0},
      {        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {         7.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -4.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         4.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -6.0,       0.0,     -3.0,        3.0,     0.0,     1.0},
      {         0.0,       0.0,     -3.0,        0.0,     0.0,    -2.0},
      {        11.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,       -1.0,     0.0,     0.0},
      {        11.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -3.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {        -1.0,       0.0,      3.0,        3.0,     0.0,    -1.0},
      {         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {         0.0,       0.0,    -13.0,        0.0,     0.0,   -11.0},
      {         3.0,       0.0,      6.0,        0.0,     0.0,     0.0},
      {        -7.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         5.0,       0.0,      0.0,       -3.0,     0.0,     0.0},
      {        -3.0,       0.0,      0.0,        1.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         5.0,       0.0,      0.0,       -3.0,     0.0,     0.0},
      {        -7.0,       0.0,      0.0,        3.0,     0.0,     0.0},
      {         8.0,       0.0,      0.0,       -3.0,     0.0,     0.0},
      {        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {        11.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -3.0,       0.0,      0.0,        1.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,       -1.0,     0.0,     0.0},
      {        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {         8.0,       0.0,      0.0,       -4.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,       -1.0,     0.0,     0.0},
      {        11.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -6.0,       0.0,      0.0,        3.0,     0.0,     0.0},
      {        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {        -8.0,       0.0,      0.0,        4.0,     0.0,     0.0},
      {        -7.0,       0.0,      0.0,        3.0,     0.0,     0.0},
      {        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,       -1.0,     0.0,     0.0},
      {         6.0,       0.0,      0.0,       -3.0,     0.0,     0.0},
      {        -6.0,       0.0,      0.0,        3.0,     0.0,     0.0},
      {         6.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         6.0,       0.0,      0.0,       -1.0,     0.0,     0.0},
      {         5.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {        -5.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {        -4.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {         4.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         6.0,       0.0,      0.0,       -3.0,     0.0,     0.0},
      {        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {         0.0,       0.0,    -26.0,        0.0,     0.0,   -11.0},
      {         0.0,       0.0,    -10.0,        0.0,     0.0,    -5.0},
      {         5.0,       0.0,      0.0,       -3.0,     0.0,     0.0},
      {       -13.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {         7.0,       0.0,      0.0,       -3.0,     0.0,     0.0},
      {         4.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         5.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -3.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {        -6.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {        -5.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {        -7.0,       0.0,      0.0,        3.0,     0.0,     0.0},
      {         5.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {        13.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {        -3.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         5.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {       -11.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         5.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {         4.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {         6.0,       0.0,      0.0,       -3.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {       -12.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         4.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -3.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -4.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,       -1.0,     0.0,     0.0},
      {        -3.0,       0.0,      0.0,        1.0,     0.0,     0.0},
      {         0.0,       0.0,     -5.0,        0.0,     0.0,    -2.0},
      {        -7.0,       0.0,      0.0,        4.0,     0.0,     0.0},
      {         6.0,       0.0,      0.0,       -3.0,     0.0,     0.0},
      {        -3.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         5.0,       0.0,      0.0,       -3.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,       -1.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -3.0,       0.0,      0.0,        1.0,     0.0,     0.0},
      {        -5.0,       0.0,      0.0,        3.0,     0.0,     0.0},
      {        -3.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {        -3.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {        12.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,       -1.0,     0.0,     0.0},
      {        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {         4.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         6.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         5.0,       0.0,      0.0,       -3.0,     0.0,     0.0},
      {         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {        -6.0,       0.0,      0.0,        3.0,     0.0,     0.0},
      {         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {         6.0,       0.0,      0.0,       -3.0,     0.0,     0.0},
      {         6.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -6.0,       0.0,      0.0,        3.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {         7.0,       0.0,      0.0,       -4.0,     0.0,     0.0},
      {         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {        -5.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {         5.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -6.0,       0.0,      0.0,        3.0,     0.0,     0.0},
      {        -6.0,       0.0,      0.0,        3.0,     0.0,     0.0},
      {        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {        10.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {         7.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         7.0,       0.0,      0.0,       -3.0,     0.0,     0.0},
      {         4.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {        11.0,       0.0,      0.0,        0.0,     0.0,     0.0},
      {         5.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {        -6.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {         5.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {        -3.0,       0.0,      0.0,        2.0,     0.0,     0.0},
      {         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0},
      {         3.0,       0.0,      0.0,       -1.0,     0.0,     0.0},
      {        -3.0,       0.0,      0.0,        1.0,     0.0,     0.0},
      {        -3.0,       0.0,      0.0,        1.0,     0.0,     0.0},
      {        -3.0,       0.0,      0.0,        2.0,     0.0,     0.0}};

/*
   Planetary argument multipliers:
       L   L'  F   D   Om  Me  Ve  E  Ma  Ju  Sa  Ur  Ne  pre
*/
   static const short int napl_t[687][14] = {
      { 0,  0,  0,  0,  0,  0,  0,  8,-16,  4,  5,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -8, 16, -4, -5,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  8,-16,  4,  5,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, -1,  2,  2},
      { 0,  0,  0,  0,  0,  0,  0, -4,  8, -1, -5,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  4, -8,  3,  0,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0,  0,  3, -8,  3,  0,  0,  0,  0},
      {-1,  0,  0,  0,  0,  0, 10, -3,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0, -2,  6, -3,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  4, -8,  3,  0,  0,  0,  0},
      { 0,  0,  1, -1,  1,  0,  0, -5,  8, -3,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -4,  8, -3,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  4, -8,  1,  5,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -5,  6,  4,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  2, -5,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  2, -5,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0,  0, -1,  0,  2, -5,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  2, -5,  0,  0,  0},
      { 0,  0,  1, -1,  1,  0,  0, -1,  0, -2,  5,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0, -2,  5,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0, -2,  5,  0,  0,  2},
      { 2,  0, -1, -1,  0,  0,  0,  3, -7,  0,  0,  0,  0,  0},
      { 1,  0,  0, -2,  0,  0, 19,-21,  3,  0,  0,  0,  0,  0},
      { 0,  0,  1, -1,  1,  0,  2, -4,  0, -3,  0,  0,  0,  0},
      { 1,  0,  0, -1,  1,  0,  0, -1,  0,  2,  0,  0,  0,  0},
      { 0,  0,  1, -1,  1,  0,  0, -1,  0, -4, 10,  0,  0,  0},
      {-2,  0,  0,  2,  1,  0,  0,  2,  0,  0, -5,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  3, -7,  4,  0,  0,  0,  0,  0},
      { 0,  0, -1,  1,  0,  0,  0,  1,  0,  1, -1,  0,  0,  0},
      {-2,  0,  0,  2,  1,  0,  0,  2,  0, -2,  0,  0,  0,  0},
      {-1,  0,  0,  0,  0,  0, 18,-16,  0,  0,  0,  0,  0,  0},
      {-2,  0,  1,  1,  2,  0,  0,  1,  0, -2,  0,  0,  0,  0},
      {-1,  0,  1, -1,  1,  0, 18,-17,  0,  0,  0,  0,  0,  0},
      {-1,  0,  0,  1,  1,  0,  0,  2, -2,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -8, 13,  0,  0,  0,  0,  0,  2},
      { 0,  0,  2, -2,  2,  0, -8, 11,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -8, 13,  0,  0,  0,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0, -8, 12,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  8,-13,  0,  0,  0,  0,  0,  0},
      { 0,  0,  1, -1,  1,  0,  8,-14,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  8,-13,  0,  0,  0,  0,  0,  1},
      {-2,  0,  0,  2,  1,  0,  0,  2,  0, -4,  5,  0,  0,  0},
      {-2,  0,  0,  2,  2,  0,  3, -3,  0,  0,  0,  0,  0,  0},
      {-2,  0,  0,  2,  0,  0,  0,  2,  0, -3,  1,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  3, -5,  0,  2,  0,  0,  0,  0},
      {-2,  0,  0,  2,  0,  0,  0,  2,  0, -4,  3,  0,  0,  0},
      { 0,  0, -1,  1,  0,  0,  0,  0,  2,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  0, -1,  2,  0,  0,  0,  0,  0},
      { 0,  0,  1, -1,  2,  0,  0, -2,  2,  0,  0,  0,  0,  0},
      {-1,  0,  1,  0,  1,  0,  3, -5,  0,  0,  0,  0,  0,  0},
      {-1,  0,  0,  1,  0,  0,  3, -4,  0,  0,  0,  0,  0,  0},
      {-2,  0,  0,  2,  0,  0,  0,  2,  0, -2, -2,  0,  0,  0},
      {-2,  0,  2,  0,  2,  0,  0, -5,  9,  0,  0,  0,  0,  0},
      { 0,  0,  1, -1,  1,  0,  0, -1,  0,  0,  0, -1,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  0,  0},
      { 0,  0,  1, -1,  1,  0,  0, -1,  0,  0,  0,  0,  2,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  2,  1},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  2,  2},
      {-1,  0,  0,  1,  0,  0,  0,  3, -4,  0,  0,  0,  0,  0},
      { 0,  0, -1,  1,  0,  0,  0,  1,  0,  0,  2,  0,  0,  0},
      { 0,  0,  1, -1,  2,  0,  0, -1,  0,  0,  2,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  0, -9, 17,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  2,  0, -3,  5,  0,  0,  0,  0,  0,  0},
      { 0,  0,  1, -1,  1,  0,  0, -1,  0, -1,  2,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  1, -2,  0,  0,  0},
      { 1,  0,  0, -2,  0,  0, 17,-16,  0, -2,  0,  0,  0,  0},
      { 0,  0,  1, -1,  1,  0,  0, -1,  0,  1, -3,  0,  0,  0},
      {-2,  0,  0,  2,  1,  0,  0,  5, -6,  0,  0,  0,  0,  0},
      { 0,  0, -2,  2,  0,  0,  0,  9,-13,  0,  0,  0,  0,  0},
      { 0,  0,  1, -1,  2,  0,  0, -1,  0,  0,  1,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  0,  0,  0,  0,  1,  0,  0,  0},
      { 0,  0, -1,  1,  0,  0,  0,  1,  0,  0,  1,  0,  0,  0},
      { 0,  0, -2,  2,  0,  0,  5, -6,  0,  0,  0,  0,  0,  0},
      { 0,  0, -1,  1,  1,  0,  5, -7,  0,  0,  0,  0,  0,  0},
      {-2,  0,  0,  2,  0,  0,  6, -8,  0,  0,  0,  0,  0,  0},
      { 2,  0,  1, -3,  1,  0, -6,  7,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  2,  0,  0,  0,  0,  1,  0,  0,  0,  0},
      { 0,  0, -1,  1,  1,  0,  0,  1,  0,  1,  0,  0,  0,  0},
      { 0,  0,  1, -1,  1,  0,  0, -1,  0,  0,  0,  2,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  2,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  2,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0, -8, 15,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0, -8, 15,  0,  0,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0,  0, -9, 15,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  8,-15,  0,  0,  0,  0,  0},
      { 1,  0, -1, -1,  0,  0,  0,  8,-15,  0,  0,  0,  0,  0},
      { 2,  0,  0, -2,  0,  0,  2, -5,  0,  0,  0,  0,  0,  0},
      {-2,  0,  0,  2,  0,  0,  0,  2,  0, -5,  5,  0,  0,  0},
      { 2,  0,  0, -2,  1,  0,  0, -6,  8,  0,  0,  0,  0,  0},
      { 2,  0,  0, -2,  1,  0,  0, -2,  0,  3,  0,  0,  0,  0},
      {-2,  0,  1,  1,  0,  0,  0,  1,  0, -3,  0,  0,  0,  0},
      {-2,  0,  1,  1,  1,  0,  0,  1,  0, -3,  0,  0,  0,  0},
      {-2,  0,  0,  2,  0,  0,  0,  2,  0, -3,  0,  0,  0,  0},
      {-2,  0,  0,  2,  0,  0,  0,  6, -8,  0,  0,  0,  0,  0},
      {-2,  0,  0,  2,  0,  0,  0,  2,  0, -1, -5,  0,  0,  0},
      {-1,  0,  0,  1,  0,  0,  0,  1,  0, -1,  0,  0,  0,  0},
      {-1,  0,  1,  1,  1,  0,-20, 20,  0,  0,  0,  0,  0,  0},
      { 1,  0,  0, -2,  0,  0, 20,-21,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  0,  8,-15,  0,  0,  0,  0,  0},
      { 0,  0,  2, -2,  1,  0,  0,-10, 15,  0,  0,  0,  0,  0},
      { 0,  0, -1,  1,  0,  0,  0,  1,  0,  1,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  0,  0,  0,  1,  0,  0,  0,  0},
      { 0,  0,  1, -1,  2,  0,  0, -1,  0,  1,  0,  0,  0,  0},
      { 0,  0,  1, -1,  1,  0,  0, -1,  0, -2,  4,  0,  0,  0},
      { 2,  0,  0, -2,  1,  0, -6,  8,  0,  0,  0,  0,  0,  0},
      { 0,  0, -2,  2,  1,  0,  5, -6,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  0, -1,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0,  0, -1,  0,  0, -1,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  0},
      { 0,  0,  1, -1,  1,  0,  0, -1,  0,  0,  1,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  2},
      { 0,  0,  2, -2,  1,  0,  0, -9, 13,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  0,  7,-13,  0,  0,  0,  0,  0},
      {-2,  0,  0,  2,  0,  0,  0,  5, -6,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  9,-17,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -9, 17,  0,  0,  0,  0,  2},
      { 1,  0,  0, -1,  1,  0,  0, -3,  4,  0,  0,  0,  0,  0},
      { 1,  0,  0, -1,  1,  0, -3,  4,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  2,  0,  0, -1,  2,  0,  0,  0,  0,  0},
      { 0,  0, -1,  1,  1,  0,  0,  0,  2,  0,  0,  0,  0,  0},
      { 0,  0, -2,  2,  0,  1,  0, -2,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  3, -5,  0,  2,  0,  0,  0,  0},
      {-2,  0,  0,  2,  1,  0,  0,  2,  0, -3,  1,  0,  0,  0},
      {-2,  0,  0,  2,  1,  0,  3, -3,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  8,-13,  0,  0,  0,  0,  0,  0},
      { 0,  0, -1,  1,  0,  0,  8,-12,  0,  0,  0,  0,  0,  0},
      { 0,  0,  2, -2,  1,  0, -8, 11,  0,  0,  0,  0,  0,  0},
      {-1,  0,  0,  1,  0,  0,  0,  2, -2,  0,  0,  0,  0,  0},
      {-1,  0,  0,  0,  1,  0, 18,-16,  0,  0,  0,  0,  0,  0},
      { 0,  0,  1, -1,  1,  0,  0, -1,  0, -1,  1,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  3, -7,  4,  0,  0,  0,  0,  0},
      {-2,  0,  1,  1,  1,  0,  0, -3,  7,  0,  0,  0,  0,  0},
      { 0,  0,  1, -1,  2,  0,  0, -1,  0, -2,  5,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  0,  0,  0, -2,  5,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  0, -4,  8, -3,  0,  0,  0,  0},
      { 1,  0,  0,  0,  1,  0,-10,  3,  0,  0,  0,  0,  0,  0},
      { 0,  0,  2, -2,  1,  0,  0, -2,  0,  0,  0,  0,  0,  0},
      {-1,  0,  0,  0,  1,  0, 10, -3,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  0,  4, -8,  3,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  0,  0,  0,  2, -5,  0,  0,  0},
      { 0,  0, -1,  1,  0,  0,  0,  1,  0,  2, -5,  0,  0,  0},
      { 2,  0, -1, -1,  1,  0,  0,  3, -7,  0,  0,  0,  0,  0},
      {-2,  0,  0,  2,  0,  0,  0,  2,  0,  0, -5,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0, -3,  7, -4,  0,  0,  0,  0,  0},
      {-2,  0,  0,  2,  0,  0,  0,  2,  0, -2,  0,  0,  0,  0},
      { 1,  0,  0,  0,  1,  0,-18, 16,  0,  0,  0,  0,  0,  0},
      {-2,  0,  1,  1,  1,  0,  0,  1,  0, -2,  0,  0,  0,  0},
      { 0,  0,  1, -1,  2,  0, -8, 12,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0, -8, 13,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  1, -2,  0,  0,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0,  0,  0, -2,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  1, -2,  0,  0,  0,  0,  0},
      { 0,  0,  1, -1,  1,  0,  0, -2,  2,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -1,  2,  0,  0,  0,  0,  1},
      {-1,  0,  0,  1,  1,  0,  3, -4,  0,  0,  0,  0,  0,  0},
      {-1,  0,  0,  1,  1,  0,  0,  3, -4,  0,  0,  0,  0,  0},
      { 0,  0,  1, -1,  1,  0,  0, -1,  0,  0, -2,  0,  0,  0},
      { 0,  0,  1, -1,  1,  0,  0, -1,  0,  0,  2,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  2},
      { 0,  0,  1, -1,  0,  0,  3, -6,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0, -3,  5,  0,  0,  0,  0,  0,  0},
      { 0,  0,  1, -1,  2,  0, -3,  4,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  0, -2,  4,  0,  0,  0,  0,  0},
      { 0,  0,  2, -2,  1,  0, -5,  6,  0,  0,  0,  0,  0,  0},
      { 0,  0, -1,  1,  0,  0,  5, -7,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  5, -8,  0,  0,  0,  0,  0,  0},
      {-2,  0,  0,  2,  1,  0,  6, -8,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  0, -8, 15,  0,  0,  0,  0,  0},
      {-2,  0,  0,  2,  1,  0,  0,  2,  0, -3,  0,  0,  0,  0},
      {-2,  0,  0,  2,  1,  0,  0,  6, -8,  0,  0,  0,  0,  0},
      { 1,  0,  0, -1,  1,  0,  0, -1,  0,  1,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  3, -5,  0,  0,  0},
      { 0,  0,  1, -1,  1,  0,  0, -1,  0, -1,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0, -1,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0,  0, -1,  0,  1,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  0,  2},
      { 0,  0,  1, -1,  2,  0,  0, -1,  0,  0, -1,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  0,  0,  0,  0, -1,  0,  0,  0},
      { 0,  0, -1,  1,  0,  0,  0,  1,  0,  0, -1,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -7, 13,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  7,-13,  0,  0,  0,  0,  0},
      { 2,  0,  0, -2,  1,  0,  0, -5,  6,  0,  0,  0,  0,  0},
      { 0,  0,  2, -2,  1,  0,  0, -8, 11,  0,  0,  0,  0,  0},
      { 0,  0,  2, -2,  1, -1,  0,  2,  0,  0,  0,  0,  0,  0},
      {-2,  0,  0,  2,  0,  0,  0,  4, -4,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  2, -2,  0,  0,  0},
      { 0,  0,  1, -1,  1,  0,  0, -1,  0,  0,  3,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  3,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  3,  0,  0,  2},
      {-2,  0,  0,  2,  0,  0,  3, -3,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  2,  0,  0, -4,  8, -3,  0,  0,  0,  0},
      { 0,  0,  0,  0,  2,  0,  0,  4, -8,  3,  0,  0,  0,  0},
      { 2,  0,  0, -2,  1,  0,  0, -2,  0,  2,  0,  0,  0,  0},
      { 0,  0,  1, -1,  2,  0,  0, -1,  0,  2,  0,  0,  0,  0},
      { 0,  0,  1, -1,  2,  0,  0,  0, -2,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  0,  1, -2,  0,  0,  0,  0,  0},
      { 0,  0, -1,  1,  0,  0,  0,  2, -2,  0,  0,  0,  0,  0},
      { 0,  0, -1,  1,  0,  0,  0,  1,  0,  0, -2,  0,  0,  0},
      { 0,  0,  2, -2,  1,  0,  0, -2,  0,  0,  2,  0,  0,  0},
      { 0,  0,  1, -1,  1,  0,  3, -6,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  3, -5,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  3, -5,  0,  0,  0,  0,  0,  0},
      { 0,  0,  1, -1,  1,  0, -3,  4,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -3,  5,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0, -3,  5,  0,  0,  0,  0,  0,  2},
      { 0,  0,  2, -2,  2,  0, -3,  3,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -3,  5,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  2, -4,  0,  0,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0,  0,  1, -4,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  2, -4,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -2,  4,  0,  0,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0,  0, -3,  4,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -2,  4,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0, -2,  4,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -5,  8,  0,  0,  0,  0,  0,  2},
      { 0,  0,  2, -2,  2,  0, -5,  6,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -5,  8,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -5,  8,  0,  0,  0,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0, -5,  7,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -5,  8,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  5, -8,  0,  0,  0,  0,  0,  0},
      { 0,  0,  1, -1,  2,  0,  0, -1,  0, -1,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  0,  0,  0, -1,  0,  0,  0,  0},
      { 0,  0, -1,  1,  0,  0,  0,  1,  0, -1,  0,  0,  0,  0},
      { 0,  0,  2, -2,  1,  0,  0, -2,  0,  1,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -6, 11,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  6,-11,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0, -1,  0,  4,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  1,  0, -4,  0,  0,  0,  0,  0,  0},
      { 2,  0,  0, -2,  1,  0, -3,  3,  0,  0,  0,  0,  0,  0},
      {-2,  0,  0,  2,  0,  0,  0,  2,  0,  0, -2,  0,  0,  0},
      { 0,  0,  2, -2,  1,  0,  0, -7,  9,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  4, -5,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0,  0, -1,  0,  2,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  2},
      { 0,  0,  2, -2,  2,  0,  0, -2,  0,  2,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  5,  0,  0,  2},
      { 0,  0,  0,  0,  1,  0,  3, -5,  0,  0,  0,  0,  0,  0},
      { 0,  0, -1,  1,  0,  0,  3, -4,  0,  0,  0,  0,  0,  0},
      { 0,  0,  2, -2,  1,  0, -3,  3,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  0,  2, -4,  0,  0,  0,  0,  0},
      { 0,  0,  2, -2,  1,  0,  0, -4,  4,  0,  0,  0,  0,  0},
      { 0,  0,  1, -1,  2,  0, -5,  7,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  3, -6,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -3,  6,  0,  0,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0,  0, -4,  6,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -3,  6,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0, -3,  6,  0,  0,  0,  0,  2},
      { 0,  0, -1,  1,  0,  0,  2, -2,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  2, -3,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -5,  9,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0, -5,  9,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  5, -9,  0,  0,  0,  0,  0},
      { 0,  0, -1,  1,  0,  0,  0,  1,  0, -2,  0,  0,  0,  0},
      { 0,  0,  2, -2,  1,  0,  0, -2,  0,  2,  0,  0,  0,  0},
      {-2,  0,  1,  1,  1,  0,  0,  1,  0,  0,  0,  0,  0,  0},
      { 0,  0, -2,  2,  0,  0,  3, -3,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -6, 10,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0, -6, 10,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -2,  3,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -2,  3,  0,  0,  0,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0, -2,  2,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  2, -3,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  2, -3,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  3,  0,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0,  0, -1,  0,  3,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  3,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  3,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  4, -8,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -4,  8,  0,  0,  0,  0,  2},
      { 0,  0, -2,  2,  0,  0,  0,  2,  0, -2,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -4,  7,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0, -4,  7,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  4, -7,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0, -2,  3,  0,  0,  0,  0,  0,  0},
      { 0,  0,  2, -2,  1,  0,  0, -2,  0,  3,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -5, 10,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  1,  0, -1,  2,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  4,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0, -3,  5,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0, -3,  5,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  3, -5,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  1, -2,  0,  0,  0,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0,  1, -3,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  1, -2,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -1,  2,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0, -1,  2,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -7, 11,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -7, 11,  0,  0,  0,  0,  0,  1},
      { 0,  0, -2,  2,  0,  0,  4, -4,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  2, -3,  0,  0,  0,  0,  0},
      { 0,  0,  2, -2,  1,  0, -4,  4,  0,  0,  0,  0,  0,  0},
      { 0,  0, -1,  1,  0,  0,  4, -5,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  1, -1,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -4,  7,  0,  0,  0,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0, -4,  6,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -4,  7,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -4,  6,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -4,  6,  0,  0,  0,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0, -4,  5,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -4,  6,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  4, -6,  0,  0,  0,  0,  0,  0},
      {-2,  0,  0,  2,  0,  0,  2, -2,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  0,  0,  0},
      { 0,  0, -1,  1,  0,  0,  1,  0,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  1, -1,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -1,  0,  5,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  1, -3,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -1,  3,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0, -7, 12,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -1,  1,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -1,  1,  0,  0,  0,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0, -1,  0,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  1, -1,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  1, -1,  0,  0,  0,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0,  1, -2,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -2,  5,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0, -1,  0,  4,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  1,  0, -4,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0, -1,  1,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -6, 10,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0, -6, 10,  0,  0,  0,  0,  0},
      { 0,  0,  2, -2,  1,  0,  0, -3,  0,  3,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -3,  7,  0,  0,  0,  0,  2},
      {-2,  0,  0,  2,  0,  0,  4, -4,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -5,  8,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  5, -8,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -1,  0,  3,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0, -1,  0,  3,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  1,  0, -3,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  2, -4,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -2,  4,  0,  0,  0,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0, -2,  3,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -2,  4,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -6,  9,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -6,  9,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  6, -9,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  0,  1,  0, -2,  0,  0,  0,  0},
      { 0,  0,  2, -2,  1,  0, -2,  2,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -4,  6,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  4, -6,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  3, -4,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -1,  0,  2,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  1,  0, -2,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  0,  1,  0, -1,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -5,  9,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  3, -4,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -3,  4,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -3,  4,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  3, -4,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  3, -4,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  1,  0,  0,  2, -2,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  0, -1,  0,  2,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  1,  0,  0, -3,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  1,  0,  1, -5,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -1,  0,  1,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  1,  0, -1,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  1,  0, -1,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  1,  0, -3,  5,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0, -3,  4,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  1,  0,  0, -2,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  2, -2,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  1,  0,  0, -1,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  0, -1,  0,  1,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  0, -2,  2,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -8, 14,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  1,  0,  2, -5,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  5, -8,  3,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  5, -8,  3,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0, -1,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  3, -8,  3,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -3,  8, -3,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  1,  0, -2,  5,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -8, 12,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -8, 12,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  1,  0,  1, -2,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  1,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  2,  0,  0,  2},
      { 0,  0,  2, -2,  1,  0, -5,  5,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  1,  0,  1,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  1,  0,  1,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  1,  0,  1,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  3, -6,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -3,  6,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0, -3,  6,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0, -1,  4,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -5,  7,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -5,  7,  0,  0,  0,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0, -5,  6,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  5, -7,  0,  0,  0,  0,  0,  0},
      { 0,  0,  2, -2,  1,  0,  0, -1,  0,  1,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -1,  0,  1,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0, -1,  0,  3,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  1,  0,  2,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0, -2,  6,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  1,  0,  2, -2,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -6,  9,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  6, -9,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -2,  2,  0,  0,  0,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0, -2,  1,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  2, -2,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  2, -2,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  1,  0,  3,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0, -5,  7,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  5, -7,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0, -2,  2,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  4, -5,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  1, -3,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -1,  3,  0,  0,  0,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0, -1,  2,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -1,  3,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -7, 10,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -7, 10,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  3, -3,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -4,  8,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -4,  5,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -4,  5,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  4, -5,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  1,  1,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0, -2,  0,  5,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  0,  3,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  1,  0,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  1,  0,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -9, 13,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0, -1,  5,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0, -2,  0,  4,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  2,  0, -4,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -2,  7,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  2,  0, -3,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -2,  5,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0, -2,  5,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -6,  8,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -6,  8,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  6, -8,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  0,  2,  0, -2,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -3,  9,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  5, -6,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  5, -6,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  2,  0, -2,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  2,  0, -2,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  2,  0, -2,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -5, 10,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  4, -4,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  4, -4,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -3,  3,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  3, -3,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  3, -3,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  3, -3,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  2,  0,  0, -3,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -5, 13,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  2,  0, -1,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  2,  0, -1,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  2,  0,  0, -2,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  2,  0,  0, -2,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  3, -2,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  3, -2,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  2,  0,  0, -1,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0, -6, 15,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -8, 15,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -3,  9, -4,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  2,  0,  2, -5,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0, -2,  8, -1, -5,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  6, -8,  3,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0,  0,  1,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0, -6, 16, -4, -5,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0, -2,  8, -3,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0, -2,  8, -3,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  6, -8,  1,  5,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  2,  0, -2,  5,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  3, -5,  4,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -8, 11,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -8, 11,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0, -8, 11,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0, 11,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  1,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  3, -3,  0,  2,  0,  0,  0,  2},
      { 0,  0,  2, -2,  1,  0,  0,  4, -8,  3,  0,  0,  0,  0},
      { 0,  0,  1, -1,  0,  0,  0,  1,  0,  0,  0,  0,  0,  0},
      { 0,  0,  2, -2,  1,  0,  0, -4,  8, -3,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  1,  2,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  2,  0,  1,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -3,  7,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  0,  4,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -5,  6,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -5,  6,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  5, -6,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  5, -6,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  2,  0,  2,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0, -1,  6,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  7, -9,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  2, -1,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  2, -1,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  6, -7,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  5, -5,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -1,  4,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0, -1,  4,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -7,  9,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -7,  9,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  4, -3,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  3, -1,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -4,  4,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  4, -4,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  4, -4,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  4, -4,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  2,  1,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0, -3,  0,  5,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  1,  1,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  1,  1,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  1,  1,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -9, 12,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  3,  0, -4,  0,  0,  0,  0},
      { 0,  0,  2, -2,  1,  0,  1, -1,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  7, -8,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  3,  0, -3,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  3,  0, -3,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -2,  6,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -6,  7,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  6, -7,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  6, -6,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  3,  0, -2,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  3,  0, -2,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  5, -4,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  3, -2,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  3, -2,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  3,  0, -1,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  3,  0, -1,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  3,  0,  0, -2,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  4, -2,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  3,  0,  0, -1,  0,  0,  2},
      { 0,  0,  2, -2,  1,  0,  0,  1,  0, -1,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -8, 16,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  3,  0,  2, -5,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  7, -8,  3,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0, -5, 16, -4, -5,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  3,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0, -1,  8, -3,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -8, 10,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -8, 10,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0, -8, 10,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  2,  2,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  3,  0,  1,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -3,  8,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -5,  5,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  5, -5,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  5, -5,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  5, -5,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  7, -7,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  7, -7,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  6, -5,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  7, -8,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  5, -3,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  4, -3,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  1,  2,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -9, 11,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -9, 11,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  4,  0, -4,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  4,  0, -3,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -6,  6,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  6, -6,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  6, -6,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  4,  0, -2,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  6, -4,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  3, -1,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  3, -1,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  3, -1,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  4,  0, -1,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  4,  0,  0, -2,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  5, -2,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  4,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  8, -9,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  5, -4,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  2,  1,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  2,  1,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  2,  1,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0, -7,  7,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  7, -7,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  4, -2,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  4, -2,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  4, -2,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  4, -2,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  5,  0, -4,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  5,  0, -3,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  5,  0, -2,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  3,  0,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -8,  8,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  8, -8,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  5, -3,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  5, -3,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -9,  9,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0, -9,  9,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0, -9,  9,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  9, -9,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  6, -4,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  6,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  6,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  6,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  6,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  6,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  6,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  6,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  6,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  2},
      { 1,  0,  0, -2,  0,  0,  0,  2,  0, -2,  0,  0,  0,  0},
      { 1,  0,  0, -2,  0,  0,  2, -2,  0,  0,  0,  0,  0,  0},
      { 1,  0,  0, -2,  0,  0,  0,  1,  0, -1,  0,  0,  0,  0},
      { 1,  0,  0, -2,  0,  0,  1, -1,  0,  0,  0,  0,  0,  0},
      {-1,  0,  0,  0,  0,  0,  3, -3,  0,  0,  0,  0,  0,  0},
      {-1,  0,  0,  0,  0,  0,  0,  2,  0, -2,  0,  0,  0,  0},
      {-1,  0,  0,  2,  0,  0,  0,  4, -8,  3,  0,  0,  0,  0},
      { 1,  0,  0, -2,  0,  0,  0,  4, -8,  3,  0,  0,  0,  0},
      {-2,  0,  0,  2,  0,  0,  0,  4, -8,  3,  0,  0,  0,  0},
      {-1,  0,  0,  0,  0,  0,  0,  2,  0, -3,  0,  0,  0,  0},
      {-1,  0,  0,  0,  0,  0,  0,  1,  0, -1,  0,  0,  0,  0},
      {-1,  0,  0,  0,  0,  0,  1, -1,  0,  0,  0,  0,  0,  0},
      {-1,  0,  0,  2,  0,  0,  2, -2,  0,  0,  0,  0,  0,  0},
      { 1,  0, -1,  1,  0,  0,  0,  1,  0,  0,  0,  0,  0,  0},
      {-1,  0,  0,  2,  0,  0,  0,  2,  0, -3,  0,  0,  0,  0},
      {-2,  0,  0,  0,  0,  0,  0,  2,  0, -3,  0,  0,  0,  0},
      { 1,  0,  0,  0,  0,  0,  0,  4, -8,  3,  0,  0,  0,  0},
      {-1,  0,  1, -1,  1,  0,  0, -1,  0,  0,  0,  0,  0,  0},
      { 1,  0,  1, -1,  1,  0,  0, -1,  0,  0,  0,  0,  0,  0},
      {-1,  0,  0,  0,  0,  0,  0,  4, -8,  3,  0,  0,  0,  0},
      {-1,  0,  0,  2,  1,  0,  0,  2,  0, -2,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  2,  0, -2,  0,  0,  0,  0},
      {-1,  0,  0,  2,  0,  0,  0,  2,  0, -2,  0,  0,  0,  0},
      {-1,  0,  0,  2,  0,  0,  3, -3,  0,  0,  0,  0,  0,  0},
      { 1,  0,  0, -2,  1,  0,  0, -2,  0,  2,  0,  0,  0,  0},
      { 1,  0,  2, -2,  2,  0, -3,  3,  0,  0,  0,  0,  0,  0},
      { 1,  0,  2, -2,  2,  0,  0, -2,  0,  2,  0,  0,  0,  0},
      { 1,  0,  0,  0,  0,  0,  1, -1,  0,  0,  0,  0,  0,  0},
      { 1,  0,  0,  0,  0,  0,  0,  1,  0, -1,  0,  0,  0,  0},
      { 0,  0,  0, -2,  0,  0,  2, -2,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0, -2,  0,  0,  0,  1,  0, -1,  0,  0,  0,  0},
      { 0,  0,  2,  0,  2,  0, -2,  2,  0,  0,  0,  0,  0,  0},
      { 0,  0,  2,  0,  2,  0,  0, -1,  0,  1,  0,  0,  0,  0},
      { 0,  0,  2,  0,  2,  0, -1,  1,  0,  0,  0,  0,  0,  0},
      { 0,  0,  2,  0,  2,  0, -2,  3,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  2,  0,  0,  0,  2,  0, -2,  0,  0,  0,  0},
      { 0,  0,  1,  1,  2,  0,  0,  1,  0,  0,  0,  0,  0,  0},
      { 1,  0,  2,  0,  2,  0,  0,  1,  0,  0,  0,  0,  0,  0},
      {-1,  0,  2,  0,  2,  0, 10, -3,  0,  0,  0,  0,  0,  0},
      { 0,  0,  1,  1,  1,  0,  0,  1,  0,  0,  0,  0,  0,  0},
      { 1,  0,  2,  0,  2,  0,  0,  1,  0,  0,  0,  0,  0,  0},
      { 0,  0,  2,  0,  2,  0,  0,  4, -8,  3,  0,  0,  0,  0},
      { 0,  0,  2,  0,  2,  0,  0, -4,  8, -3,  0,  0,  0,  0},
      {-1,  0,  2,  0,  2,  0,  0, -4,  8, -3,  0,  0,  0,  0},
      { 2,  0,  2, -2,  2,  0,  0, -2,  0,  3,  0,  0,  0,  0},
      { 1,  0,  2,  0,  1,  0,  0, -2,  0,  3,  0,  0,  0,  0},
      { 0,  0,  1,  1,  0,  0,  0,  1,  0,  0,  0,  0,  0,  0},
      {-1,  0,  2,  0,  1,  0,  0,  1,  0,  0,  0,  0,  0,  0},
      {-2,  0,  2,  2,  2,  0,  0,  2,  0, -2,  0,  0,  0,  0},
      { 0,  0,  2,  0,  2,  0,  2, -3,  0,  0,  0,  0,  0,  0},
      { 0,  0,  2,  0,  2,  0,  1, -1,  0,  0,  0,  0,  0,  0},
      { 0,  0,  2,  0,  2,  0,  0,  1,  0, -1,  0,  0,  0,  0},
      { 0,  0,  2,  0,  2,  0,  2, -2,  0,  0,  0,  0,  0,  0},
      {-1,  0,  2,  2,  2,  0,  0, -1,  0,  1,  0,  0,  0,  0},
      { 1,  0,  2,  0,  2,  0, -1,  1,  0,  0,  0,  0,  0,  0},
      {-1,  0,  2,  2,  2,  0,  0,  2,  0, -3,  0,  0,  0,  0},
      { 2,  0,  2,  0,  2,  0,  0,  2,  0, -3,  0,  0,  0,  0},
      { 1,  0,  2,  0,  2,  0,  0, -4,  8, -3,  0,  0,  0,  0},
      { 1,  0,  2,  0,  2,  0,  0,  4, -8,  3,  0,  0,  0,  0},
      { 1,  0,  1,  1,  1,  0,  0,  1,  0,  0,  0,  0,  0,  0},
      { 0,  0,  2,  0,  2,  0,  0,  1,  0,  0,  0,  0,  0,  0},
      { 2,  0,  2,  0,  1,  0,  0,  1,  0,  0,  0,  0,  0,  0},
      {-1,  0,  2,  2,  2,  0,  0,  2,  0, -2,  0,  0,  0,  0},
      {-1,  0,  2,  2,  2,  0,  3, -3,  0,  0,  0,  0,  0,  0},
      { 1,  0,  2,  0,  2,  0,  1, -1,  0,  0,  0,  0,  0,  0},
      { 0,  0,  2,  2,  2,  0,  0,  2,  0, -2,  0,  0,  0,  0}};

/*
   Planetary nutation coefficients, unit 1e-7 arcsec:
   longitude (sin, cos), obliquity (sin, cos)

   Each row of coefficients in 'cpl_t' belongs with the corresponding
   row of fundamental-argument multipliers in 'napl_t'.
*/

   static const double cpl_t[687][4] = {
      { 1440.0,          0.0,          0.0,          0.0},
      {   56.0,       -117.0,        -42.0,        -40.0},
      {  125.0,        -43.0,          0.0,        -54.0},
      {    0.0,          5.0,          0.0,          0.0},
      {    3.0,         -7.0,         -3.0,          0.0},
      {    3.0,          0.0,          0.0,         -2.0},
      { -114.0,          0.0,          0.0,         61.0},
      { -219.0,         89.0,          0.0,          0.0},
      {   -3.0,          0.0,          0.0,          0.0},
      { -462.0,       1604.0,          0.0,          0.0},
      {   99.0,          0.0,          0.0,        -53.0},
      {   -3.0,          0.0,          0.0,          2.0},
      {    0.0,          6.0,          2.0,          0.0},
      {    3.0,          0.0,          0.0,          0.0},
      {  -12.0,          0.0,          0.0,          0.0},
      {   14.0,       -218.0,        117.0,          8.0},
      {   31.0,       -481.0,       -257.0,        -17.0},
      { -491.0,        128.0,          0.0,          0.0},
      {-3084.0,       5123.0,       2735.0,       1647.0},
      {-1444.0,       2409.0,      -1286.0,       -771.0},
      {   11.0,        -24.0,        -11.0,         -9.0},
      {   26.0,         -9.0,          0.0,          0.0},
      {  103.0,        -60.0,          0.0,          0.0},
      {    0.0,        -13.0,         -7.0,          0.0},
      {  -26.0,        -29.0,        -16.0,         14.0},
      {    9.0,        -27.0,        -14.0,         -5.0},
      {   12.0,          0.0,          0.0,         -6.0},
      {   -7.0,          0.0,          0.0,          0.0},
      {    0.0,         24.0,          0.0,          0.0},
      {  284.0,          0.0,          0.0,       -151.0},
      {  226.0,        101.0,          0.0,          0.0},
      {    0.0,         -8.0,         -2.0,          0.0},
      {    0.0,         -6.0,         -3.0,          0.0},
      {    5.0,          0.0,          0.0,         -3.0},
      {  -41.0,        175.0,         76.0,         17.0},
      {    0.0,         15.0,          6.0,          0.0},
      {  425.0,        212.0,       -133.0,        269.0},
      { 1200.0,        598.0,        319.0,       -641.0},
      {  235.0,        334.0,          0.0,          0.0},
      {   11.0,        -12.0,         -7.0,         -6.0},
      {    5.0,         -6.0,          3.0,          3.0},
      {   -5.0,          0.0,          0.0,          3.0},
      {    6.0,          0.0,          0.0,         -3.0},
      {   15.0,          0.0,          0.0,          0.0},
      {   13.0,          0.0,          0.0,         -7.0},
      {   -6.0,         -9.0,          0.0,          0.0},
      {  266.0,        -78.0,          0.0,          0.0},
      { -460.0,       -435.0,       -232.0,        246.0},
      {    0.0,         15.0,          7.0,          0.0},
      {   -3.0,          0.0,          0.0,          2.0},
      {    0.0,        131.0,          0.0,          0.0},
      {    4.0,          0.0,          0.0,          0.0},
      {    0.0,          3.0,          0.0,          0.0},
      {    0.0,          4.0,          2.0,          0.0},
      {    0.0,          3.0,          0.0,          0.0},
      {  -17.0,        -19.0,        -10.0,          9.0},
      {   -9.0,        -11.0,          6.0,         -5.0},
      {   -6.0,          0.0,          0.0,          3.0},
      {  -16.0,          8.0,          0.0,          0.0},
      {    0.0,          3.0,          0.0,          0.0},
      {   11.0,         24.0,         11.0,         -5.0},
      {   -3.0,         -4.0,         -2.0,          1.0},
      {    3.0,          0.0,          0.0,         -1.0},
      {    0.0,         -8.0,         -4.0,          0.0},
      {    0.0,          3.0,          0.0,          0.0},
      {    0.0,          5.0,          0.0,          0.0},
      {    0.0,          3.0,          2.0,          0.0},
      {   -6.0,          4.0,          2.0,          3.0},
      {   -3.0,         -5.0,          0.0,          0.0},
      {   -5.0,          0.0,          0.0,          2.0},
      {    4.0,         24.0,         13.0,         -2.0},
      {  -42.0,         20.0,          0.0,          0.0},
      {  -10.0,        233.0,          0.0,          0.0},
      {   -3.0,          0.0,          0.0,          1.0},
      {   78.0,        -18.0,          0.0,          0.0},
      {    0.0,          3.0,          1.0,          0.0},
      {    0.0,         -3.0,         -1.0,          0.0},
      {    0.0,         -4.0,         -2.0,          1.0},
      {    0.0,         -8.0,         -4.0,         -1.0},
      {    0.0,         -5.0,          3.0,          0.0},
      {   -7.0,          0.0,          0.0,          3.0},
      {  -14.0,          8.0,          3.0,          6.0},
      {    0.0,          8.0,         -4.0,          0.0},
      {    0.0,         19.0,         10.0,          0.0},
      {   45.0,        -22.0,          0.0,          0.0},
      {   -3.0,          0.0,          0.0,          0.0},
      {    0.0,         -3.0,          0.0,          0.0},
      {    0.0,          3.0,          0.0,          0.0},
      {    3.0,          5.0,          3.0,         -2.0},
      {   89.0,        -16.0,         -9.0,        -48.0},
      {    0.0,          3.0,          0.0,          0.0},
      {   -3.0,          7.0,          4.0,          2.0},
      { -349.0,        -62.0,          0.0,          0.0},
      {  -15.0,         22.0,          0.0,          0.0},
      {   -3.0,          0.0,          0.0,          0.0},
      {  -53.0,          0.0,          0.0,          0.0},
      {    5.0,          0.0,          0.0,         -3.0},
      {    0.0,         -8.0,          0.0,          0.0},
      {   15.0,         -7.0,         -4.0,         -8.0},
      {   -3.0,          0.0,          0.0,          1.0},
      {  -21.0,        -78.0,          0.0,          0.0},
      {   20.0,        -70.0,        -37.0,        -11.0},
      {    0.0,          6.0,          3.0,          0.0},
      {    5.0,          3.0,          2.0,         -2.0},
      {  -17.0,         -4.0,         -2.0,          9.0},
      {    0.0,          6.0,          3.0,          0.0},
      {   32.0,         15.0,         -8.0,         17.0},
      {  174.0,         84.0,         45.0,        -93.0},
      {   11.0,         56.0,          0.0,          0.0},
      {  -66.0,        -12.0,         -6.0,         35.0},
      {   47.0,          8.0,          4.0,        -25.0},
      {    0.0,          8.0,          4.0,          0.0},
      {   10.0,        -22.0,        -12.0,         -5.0},
      {   -3.0,          0.0,          0.0,          2.0},
      {  -24.0,         12.0,          0.0,          0.0},
      {    5.0,         -6.0,          0.0,          0.0},
      {    3.0,          0.0,          0.0,         -2.0},
      {    4.0,          3.0,          1.0,         -2.0},
      {    0.0,         29.0,         15.0,          0.0},
      {   -5.0,         -4.0,         -2.0,          2.0},
      {    8.0,         -3.0,         -1.0,         -5.0},
      {    0.0,         -3.0,          0.0,          0.0},
      {   10.0,          0.0,          0.0,          0.0},
      {    3.0,          0.0,          0.0,         -2.0},
      {   -5.0,          0.0,          0.0,          3.0},
      {   46.0,         66.0,         35.0,        -25.0},
      {  -14.0,          7.0,          0.0,          0.0},
      {    0.0,          3.0,          2.0,          0.0},
      {   -5.0,          0.0,          0.0,          0.0},
      {  -68.0,        -34.0,        -18.0,         36.0},
      {    0.0,         14.0,          7.0,          0.0},
      {   10.0,         -6.0,         -3.0,         -5.0},
      {   -5.0,         -4.0,         -2.0,          3.0},
      {   -3.0,          5.0,          2.0,          1.0},
      {   76.0,         17.0,          9.0,        -41.0},
      {   84.0,        298.0,        159.0,        -45.0},
      {    3.0,          0.0,          0.0,         -1.0},
      {   -3.0,          0.0,          0.0,          2.0},
      {   -3.0,          0.0,          0.0,          1.0},
      {  -82.0,        292.0,        156.0,         44.0},
      {  -73.0,         17.0,          9.0,         39.0},
      {   -9.0,        -16.0,          0.0,          0.0},
      {    3.0,          0.0,         -1.0,         -2.0},
      {   -3.0,          0.0,          0.0,          0.0},
      {   -9.0,         -5.0,         -3.0,          5.0},
      { -439.0,          0.0,          0.0,          0.0},
      {   57.0,        -28.0,        -15.0,        -30.0},
      {    0.0,         -6.0,         -3.0,          0.0},
      {   -4.0,          0.0,          0.0,          2.0},
      {  -40.0,         57.0,         30.0,         21.0},
      {   23.0,          7.0,          3.0,        -13.0},
      {  273.0,         80.0,         43.0,       -146.0},
      { -449.0,        430.0,          0.0,          0.0},
      {   -8.0,        -47.0,        -25.0,          4.0},
      {    6.0,         47.0,         25.0,         -3.0},
      {    0.0,         23.0,         13.0,          0.0},
      {   -3.0,          0.0,          0.0,          2.0},
      {    3.0,         -4.0,         -2.0,         -2.0},
      {  -48.0,       -110.0,        -59.0,         26.0},
      {   51.0,        114.0,         61.0,        -27.0},
      { -133.0,          0.0,          0.0,         57.0},
      {    0.0,          4.0,          0.0,          0.0},
      {  -21.0,         -6.0,         -3.0,         11.0},
      {    0.0,         -3.0,         -1.0,          0.0},
      {  -11.0,        -21.0,        -11.0,          6.0},
      {  -18.0,       -436.0,       -233.0,          9.0},
      {   35.0,         -7.0,          0.0,          0.0},
      {    0.0,          5.0,          3.0,          0.0},
      {   11.0,         -3.0,         -1.0,         -6.0},
      {   -5.0,         -3.0,         -1.0,          3.0},
      {  -53.0,         -9.0,         -5.0,         28.0},
      {    0.0,          3.0,          2.0,          1.0},
      {    4.0,          0.0,          0.0,         -2.0},
      {    0.0,         -4.0,          0.0,          0.0},
      {  -50.0,        194.0,        103.0,         27.0},
      {  -13.0,         52.0,         28.0,          7.0},
      {  -91.0,        248.0,          0.0,          0.0},
      {    6.0,         49.0,         26.0,         -3.0},
      {   -6.0,        -47.0,        -25.0,          3.0},
      {    0.0,          5.0,          3.0,          0.0},
      {   52.0,         23.0,         10.0,        -23.0},
      {   -3.0,          0.0,          0.0,          1.0},
      {    0.0,          5.0,          3.0,          0.0},
      {   -4.0,          0.0,          0.0,          0.0},
      {   -4.0,          8.0,          3.0,          2.0},
      {   10.0,          0.0,          0.0,          0.0},
      {    3.0,          0.0,          0.0,         -2.0},
      {    0.0,          8.0,          4.0,          0.0},
      {    0.0,          8.0,          4.0,          1.0},
      {   -4.0,          0.0,          0.0,          0.0},
      {   -4.0,          0.0,          0.0,          0.0},
      {   -8.0,          4.0,          2.0,          4.0},
      {    8.0,         -4.0,         -2.0,         -4.0},
      {    0.0,         15.0,          7.0,          0.0},
      { -138.0,          0.0,          0.0,          0.0},
      {    0.0,         -7.0,         -3.0,          0.0},
      {    0.0,         -7.0,         -3.0,          0.0},
      {   54.0,          0.0,          0.0,        -29.0},
      {    0.0,         10.0,          4.0,          0.0},
      {   -7.0,          0.0,          0.0,          3.0},
      {  -37.0,         35.0,         19.0,         20.0},
      {    0.0,          4.0,          0.0,          0.0},
      {   -4.0,          9.0,          0.0,          0.0},
      {    8.0,          0.0,          0.0,         -4.0},
      {   -9.0,        -14.0,         -8.0,          5.0},
      {   -3.0,         -9.0,         -5.0,          3.0},
      { -145.0,         47.0,          0.0,          0.0},
      {  -10.0,         40.0,         21.0,          5.0},
      {   11.0,        -49.0,        -26.0,         -7.0},
      {-2150.0,          0.0,          0.0,        932.0},
      {  -12.0,          0.0,          0.0,          5.0},
      {   85.0,          0.0,          0.0,        -37.0},
      {    4.0,          0.0,          0.0,         -2.0},
      {    3.0,          0.0,          0.0,         -2.0},
      {  -86.0,        153.0,          0.0,          0.0},
      {   -6.0,          9.0,          5.0,          3.0},
      {    9.0,        -13.0,         -7.0,         -5.0},
      {   -8.0,         12.0,          6.0,          4.0},
      {  -51.0,          0.0,          0.0,         22.0},
      {  -11.0,       -268.0,       -116.0,          5.0},
      {    0.0,         12.0,          5.0,          0.0},
      {    0.0,          7.0,          3.0,          0.0},
      {   31.0,          6.0,          3.0,        -17.0},
      {  140.0,         27.0,         14.0,        -75.0},
      {   57.0,         11.0,          6.0,        -30.0},
      {  -14.0,        -39.0,          0.0,          0.0},
      {    0.0,         -6.0,         -2.0,          0.0},
      {    4.0,         15.0,          8.0,         -2.0},
      {    0.0,          4.0,          0.0,          0.0},
      {   -3.0,          0.0,          0.0,          1.0},
      {    0.0,         11.0,          5.0,          0.0},
      {    9.0,          6.0,          0.0,          0.0},
      {   -4.0,         10.0,          4.0,          2.0},
      {    5.0,          3.0,          0.0,          0.0},
      {   16.0,          0.0,          0.0,         -9.0},
      {   -3.0,          0.0,          0.0,          0.0},
      {    0.0,          3.0,          2.0,         -1.0},
      {    7.0,          0.0,          0.0,         -3.0},
      {  -25.0,         22.0,          0.0,          0.0},
      {   42.0,        223.0,        119.0,        -22.0},
      {  -27.0,       -143.0,        -77.0,         14.0},
      {    9.0,         49.0,         26.0,         -5.0},
      {-1166.0,          0.0,          0.0,        505.0},
      {   -5.0,          0.0,          0.0,          2.0},
      {   -6.0,          0.0,          0.0,          3.0},
      {   -8.0,          0.0,          1.0,          4.0},
      {    0.0,         -4.0,          0.0,          0.0},
      {  117.0,          0.0,          0.0,        -63.0},
      {   -4.0,          8.0,          4.0,          2.0},
      {    3.0,          0.0,          0.0,         -2.0},
      {   -5.0,          0.0,          0.0,          2.0},
      {    0.0,         31.0,          0.0,          0.0},
      {   -5.0,          0.0,          1.0,          3.0},
      {    4.0,          0.0,          0.0,         -2.0},
      {   -4.0,          0.0,          0.0,          2.0},
      {  -24.0,        -13.0,         -6.0,         10.0},
      {    3.0,          0.0,          0.0,          0.0},
      {    0.0,        -32.0,        -17.0,          0.0},
      {    8.0,         12.0,          5.0,         -3.0},
      {    3.0,          0.0,          0.0,         -1.0},
      {    7.0,         13.0,          0.0,          0.0},
      {   -3.0,         16.0,          0.0,          0.0},
      {   50.0,          0.0,          0.0,        -27.0},
      {    0.0,         -5.0,         -3.0,          0.0},
      {   13.0,          0.0,          0.0,          0.0},
      {    0.0,          5.0,          3.0,          1.0},
      {   24.0,          5.0,          2.0,        -11.0},
      {    5.0,        -11.0,         -5.0,         -2.0},
      {   30.0,         -3.0,         -2.0,        -16.0},
      {   18.0,          0.0,          0.0,         -9.0},
      {    8.0,        614.0,          0.0,          0.0},
      {    3.0,         -3.0,         -1.0,         -2.0},
      {    6.0,         17.0,          9.0,         -3.0},
      {   -3.0,         -9.0,         -5.0,          2.0},
      {    0.0,          6.0,          3.0,         -1.0},
      { -127.0,         21.0,          9.0,         55.0},
      {    3.0,          5.0,          0.0,          0.0},
      {   -6.0,        -10.0,         -4.0,          3.0},
      {    5.0,          0.0,          0.0,          0.0},
      {   16.0,          9.0,          4.0,         -7.0},
      {    3.0,          0.0,          0.0,         -2.0},
      {    0.0,         22.0,          0.0,          0.0},
      {    0.0,         19.0,         10.0,          0.0},
      {    7.0,          0.0,          0.0,         -4.0},
      {    0.0,         -5.0,         -2.0,          0.0},
      {    0.0,          3.0,          1.0,          0.0},
      {   -9.0,          3.0,          1.0,          4.0},
      {   17.0,          0.0,          0.0,         -7.0},
      {    0.0,         -3.0,         -2.0,         -1.0},
      {  -20.0,         34.0,          0.0,          0.0},
      {  -10.0,          0.0,          1.0,          5.0},
      {   -4.0,          0.0,          0.0,          2.0},
      {   22.0,        -87.0,          0.0,          0.0},
      {   -4.0,          0.0,          0.0,          2.0},
      {   -3.0,         -6.0,         -2.0,          1.0},
      {  -16.0,         -3.0,         -1.0,          7.0},
      {    0.0,         -3.0,         -2.0,          0.0},
      {    4.0,          0.0,          0.0,          0.0},
      {  -68.0,         39.0,          0.0,          0.0},
      {   27.0,          0.0,          0.0,        -14.0},
      {    0.0,         -4.0,          0.0,          0.0},
      {  -25.0,          0.0,          0.0,          0.0},
      {  -12.0,         -3.0,         -2.0,          6.0},
      {    3.0,          0.0,          0.0,         -1.0},
      {    3.0,         66.0,         29.0,         -1.0},
      {  490.0,          0.0,          0.0,       -213.0},
      {  -22.0,         93.0,         49.0,         12.0},
      {   -7.0,         28.0,         15.0,          4.0},
      {   -3.0,         13.0,          7.0,          2.0},
      {  -46.0,         14.0,          0.0,          0.0},
      {   -5.0,          0.0,          0.0,          0.0},
      {    2.0,          1.0,          0.0,          0.0},
      {    0.0,         -3.0,          0.0,          0.0},
      {  -28.0,          0.0,          0.0,         15.0},
      {    5.0,          0.0,          0.0,         -2.0},
      {    0.0,          3.0,          0.0,          0.0},
      {  -11.0,          0.0,          0.0,          5.0},
      {    0.0,          3.0,          1.0,          0.0},
      {   -3.0,          0.0,          0.0,          1.0},
      {   25.0,        106.0,         57.0,        -13.0},
      {    5.0,         21.0,         11.0,         -3.0},
      { 1485.0,          0.0,          0.0,          0.0},
      {   -7.0,        -32.0,        -17.0,          4.0},
      {    0.0,          5.0,          3.0,          0.0},
      {   -6.0,         -3.0,         -2.0,          3.0},
      {   30.0,         -6.0,         -2.0,        -13.0},
      {   -4.0,          4.0,          0.0,          0.0},
      {  -19.0,          0.0,          0.0,         10.0},
      {    0.0,          4.0,          2.0,         -1.0},
      {    0.0,          3.0,          0.0,          0.0},
      {    4.0,          0.0,          0.0,         -2.0},
      {    0.0,         -3.0,         -1.0,          0.0},
      {   -3.0,          0.0,          0.0,          0.0},
      {    5.0,          3.0,          1.0,         -2.0},
      {    0.0,         11.0,          0.0,          0.0},
      {  118.0,          0.0,          0.0,        -52.0},
      {    0.0,         -5.0,         -3.0,          0.0},
      {  -28.0,         36.0,          0.0,          0.0},
      {    5.0,         -5.0,          0.0,          0.0},
      {   14.0,        -59.0,        -31.0,         -8.0},
      {    0.0,          9.0,          5.0,          1.0},
      { -458.0,          0.0,          0.0,        198.0},
      {    0.0,        -45.0,        -20.0,          0.0},
      {    9.0,          0.0,          0.0,         -5.0},
      {    0.0,         -3.0,          0.0,          0.0},
      {    0.0,         -4.0,         -2.0,         -1.0},
      {   11.0,          0.0,          0.0,         -6.0},
      {    6.0,          0.0,          0.0,         -2.0},
      {  -16.0,         23.0,          0.0,          0.0},
      {    0.0,         -4.0,         -2.0,          0.0},
      {   -5.0,          0.0,          0.0,          2.0},
      { -166.0,        269.0,          0.0,          0.0},
      {   15.0,          0.0,          0.0,         -8.0},
      {   10.0,          0.0,          0.0,         -4.0},
      {  -78.0,         45.0,          0.0,          0.0},
      {    0.0,         -5.0,         -2.0,          0.0},
      {    7.0,          0.0,          0.0,         -4.0},
      {   -5.0,        328.0,          0.0,          0.0},
      {    3.0,          0.0,          0.0,         -2.0},
      {    5.0,          0.0,          0.0,         -2.0},
      {    0.0,          3.0,          1.0,          0.0},
      {   -3.0,          0.0,          0.0,          0.0},
      {   -3.0,          0.0,          0.0,          0.0},
      {    0.0,         -4.0,         -2.0,          0.0},
      {-1223.0,        -26.0,          0.0,          0.0},
      {    0.0,          7.0,          3.0,          0.0},
      {    3.0,          0.0,          0.0,          0.0},
      {    0.0,          3.0,          2.0,          0.0},
      {   -6.0,         20.0,          0.0,          0.0},
      { -368.0,          0.0,          0.0,          0.0},
      {  -75.0,          0.0,          0.0,          0.0},
      {   11.0,          0.0,          0.0,         -6.0},
      {    3.0,          0.0,          0.0,         -2.0},
      {   -3.0,          0.0,          0.0,          1.0},
      {  -13.0,        -30.0,          0.0,          0.0},
      {   21.0,          3.0,          0.0,          0.0},
      {   -3.0,          0.0,          0.0,          1.0},
      {   -4.0,          0.0,          0.0,          2.0},
      {    8.0,        -27.0,          0.0,          0.0},
      {  -19.0,        -11.0,          0.0,          0.0},
      {   -4.0,          0.0,          0.0,          2.0},
      {    0.0,          5.0,          2.0,          0.0},
      {   -6.0,          0.0,          0.0,          2.0},
      {   -8.0,          0.0,          0.0,          0.0},
      {   -1.0,          0.0,          0.0,          0.0},
      {  -14.0,          0.0,          0.0,          6.0},
      {    6.0,          0.0,          0.0,          0.0},
      {  -74.0,          0.0,          0.0,         32.0},
      {    0.0,         -3.0,         -1.0,          0.0},
      {    4.0,          0.0,          0.0,         -2.0},
      {    8.0,         11.0,          0.0,          0.0},
      {    0.0,          3.0,          2.0,          0.0},
      { -262.0,          0.0,          0.0,        114.0},
      {    0.0,         -4.0,          0.0,          0.0},
      {   -7.0,          0.0,          0.0,          4.0},
      {    0.0,        -27.0,        -12.0,          0.0},
      {  -19.0,         -8.0,         -4.0,          8.0},
      {  202.0,          0.0,          0.0,        -87.0},
      {   -8.0,         35.0,         19.0,          5.0},
      {    0.0,          4.0,          2.0,          0.0},
      {   16.0,         -5.0,          0.0,          0.0},
      {    5.0,          0.0,          0.0,         -3.0},
      {    0.0,         -3.0,          0.0,          0.0},
      {    1.0,          0.0,          0.0,          0.0},
      {  -35.0,        -48.0,        -21.0,         15.0},
      {   -3.0,         -5.0,         -2.0,          1.0},
      {    6.0,          0.0,          0.0,         -3.0},
      {    3.0,          0.0,          0.0,         -1.0},
      {    0.0,         -5.0,          0.0,          0.0},
      {   12.0,         55.0,         29.0,         -6.0},
      {    0.0,          5.0,          3.0,          0.0},
      { -598.0,          0.0,          0.0,          0.0},
      {   -3.0,        -13.0,         -7.0,          1.0},
      {   -5.0,         -7.0,         -3.0,          2.0},
      {    3.0,          0.0,          0.0,         -1.0},
      {    5.0,         -7.0,          0.0,          0.0},
      {    4.0,          0.0,          0.0,         -2.0},
      {   16.0,         -6.0,          0.0,          0.0},
      {    8.0,         -3.0,          0.0,          0.0},
      {    8.0,        -31.0,        -16.0,         -4.0},
      {    0.0,          3.0,          1.0,          0.0},
      {  113.0,          0.0,          0.0,        -49.0},
      {    0.0,        -24.0,        -10.0,          0.0},
      {    4.0,          0.0,          0.0,         -2.0},
      {   27.0,          0.0,          0.0,          0.0},
      {   -3.0,          0.0,          0.0,          1.0},
      {    0.0,         -4.0,         -2.0,          0.0},
      {    5.0,          0.0,          0.0,         -2.0},
      {    0.0,         -3.0,          0.0,          0.0},
      {  -13.0,          0.0,          0.0,          6.0},
      {    5.0,          0.0,          0.0,         -2.0},
      {  -18.0,        -10.0,         -4.0,          8.0},
      {   -4.0,        -28.0,          0.0,          0.0},
      {   -5.0,          6.0,          3.0,          2.0},
      {   -3.0,          0.0,          0.0,          1.0},
      {   -5.0,         -9.0,         -4.0,          2.0},
      {   17.0,          0.0,          0.0,         -7.0},
      {   11.0,          4.0,          0.0,          0.0},
      {    0.0,         -6.0,         -2.0,          0.0},
      {   83.0,         15.0,          0.0,          0.0},
      {   -4.0,          0.0,          0.0,          2.0},
      {    0.0,       -114.0,        -49.0,          0.0},
      {  117.0,          0.0,          0.0,        -51.0},
      {   -5.0,         19.0,         10.0,          2.0},
      {   -3.0,          0.0,          0.0,          0.0},
      {   -3.0,          0.0,          0.0,          2.0},
      {    0.0,         -3.0,         -1.0,          0.0},
      {    3.0,          0.0,          0.0,          0.0},
      {    0.0,         -6.0,         -2.0,          0.0},
      {  393.0,          3.0,          0.0,          0.0},
      {   -4.0,         21.0,         11.0,          2.0},
      {   -6.0,          0.0,         -1.0,          3.0},
      {   -3.0,          8.0,          4.0,          1.0},
      {    8.0,          0.0,          0.0,          0.0},
      {   18.0,        -29.0,        -13.0,         -8.0},
      {    8.0,         34.0,         18.0,         -4.0},
      {   89.0,          0.0,          0.0,          0.0},
      {    3.0,         12.0,          6.0,         -1.0},
      {   54.0,        -15.0,         -7.0,        -24.0},
      {    0.0,          3.0,          0.0,          0.0},
      {    3.0,          0.0,          0.0,         -1.0},
      {    0.0,         35.0,          0.0,          0.0},
      { -154.0,        -30.0,        -13.0,         67.0},
      {   15.0,          0.0,          0.0,          0.0},
      {    0.0,          4.0,          2.0,          0.0},
      {    0.0,          9.0,          0.0,          0.0},
      {   80.0,        -71.0,        -31.0,        -35.0},
      {    0.0,        -20.0,         -9.0,          0.0},
      {   11.0,          5.0,          2.0,         -5.0},
      {   61.0,        -96.0,        -42.0,        -27.0},
      {   14.0,          9.0,          4.0,         -6.0},
      {  -11.0,         -6.0,         -3.0,          5.0},
      {    0.0,         -3.0,         -1.0,          0.0},
      {  123.0,       -415.0,       -180.0,        -53.0},
      {    0.0,          0.0,          0.0,        -35.0},
      {   -5.0,          0.0,          0.0,          0.0},
      {    7.0,        -32.0,        -17.0,         -4.0},
      {    0.0,         -9.0,         -5.0,          0.0},
      {    0.0,         -4.0,          2.0,          0.0},
      {  -89.0,          0.0,          0.0,         38.0},
      {    0.0,        -86.0,        -19.0,         -6.0},
      {    0.0,          0.0,        -19.0,          6.0},
      { -123.0,       -416.0,       -180.0,         53.0},
      {    0.0,         -3.0,         -1.0,          0.0},
      {   12.0,         -6.0,         -3.0,         -5.0},
      {  -13.0,          9.0,          4.0,          6.0},
      {    0.0,        -15.0,         -7.0,          0.0},
      {    3.0,          0.0,          0.0,         -1.0},
      {  -62.0,        -97.0,        -42.0,         27.0},
      {  -11.0,          5.0,          2.0,          5.0},
      {    0.0,        -19.0,         -8.0,          0.0},
      {   -3.0,          0.0,          0.0,          1.0},
      {    0.0,          4.0,          2.0,          0.0},
      {    0.0,          3.0,          0.0,          0.0},
      {    0.0,          4.0,          2.0,          0.0},
      {  -85.0,        -70.0,        -31.0,         37.0},
      {  163.0,        -12.0,         -5.0,        -72.0},
      {  -63.0,        -16.0,         -7.0,         28.0},
      {  -21.0,        -32.0,        -14.0,          9.0},
      {    0.0,         -3.0,         -1.0,          0.0},
      {    3.0,          0.0,          0.0,         -2.0},
      {    0.0,          8.0,          0.0,          0.0},
      {    3.0,         10.0,          4.0,         -1.0},
      {    3.0,          0.0,          0.0,         -1.0},
      {    0.0,         -7.0,         -3.0,          0.0},
      {    0.0,         -4.0,         -2.0,          0.0},
      {    6.0,         19.0,          0.0,          0.0},
      {    5.0,       -173.0,        -75.0,         -2.0},
      {    0.0,         -7.0,         -3.0,          0.0},
      {    7.0,        -12.0,         -5.0,         -3.0},
      {   -3.0,          0.0,          0.0,          2.0},
      {    3.0,         -4.0,         -2.0,         -1.0},
      {   74.0,          0.0,          0.0,        -32.0},
      {   -3.0,         12.0,          6.0,          2.0},
      {   26.0,        -14.0,         -6.0,        -11.0},
      {   19.0,          0.0,          0.0,         -8.0},
      {    6.0,         24.0,         13.0,         -3.0},
      {   83.0,          0.0,          0.0,          0.0},
      {    0.0,        -10.0,         -5.0,          0.0},
      {   11.0,         -3.0,         -1.0,         -5.0},
      {    3.0,          0.0,          1.0,         -1.0},
      {    3.0,          0.0,          0.0,         -1.0},
      {   -4.0,          0.0,          0.0,          0.0},
      {    5.0,        -23.0,        -12.0,         -3.0},
      { -339.0,          0.0,          0.0,        147.0},
      {    0.0,        -10.0,         -5.0,          0.0},
      {    5.0,          0.0,          0.0,          0.0},
      {    3.0,          0.0,          0.0,         -1.0},
      {    0.0,         -4.0,         -2.0,          0.0},
      {   18.0,         -3.0,          0.0,          0.0},
      {    9.0,        -11.0,         -5.0,         -4.0},
      {   -8.0,          0.0,          0.0,          4.0},
      {    3.0,          0.0,          0.0,         -1.0},
      {    0.0,          9.0,          0.0,          0.0},
      {    6.0,         -9.0,         -4.0,         -2.0},
      {   -4.0,        -12.0,          0.0,          0.0},
      {   67.0,        -91.0,        -39.0,        -29.0},
      {   30.0,        -18.0,         -8.0,        -13.0},
      {    0.0,          0.0,          0.0,          0.0},
      {    0.0,       -114.0,        -50.0,          0.0},
      {    0.0,          0.0,          0.0,         23.0},
      {  517.0,         16.0,          7.0,       -224.0},
      {    0.0,         -7.0,         -3.0,          0.0},
      {  143.0,         -3.0,         -1.0,        -62.0},
      {   29.0,          0.0,          0.0,        -13.0},
      {   -4.0,          0.0,          0.0,          2.0},
      {   -6.0,          0.0,          0.0,          3.0},
      {    5.0,         12.0,          5.0,         -2.0},
      {  -25.0,          0.0,          0.0,         11.0},
      {   -3.0,          0.0,          0.0,          1.0},
      {    0.0,          4.0,          2.0,          0.0},
      {  -22.0,         12.0,          5.0,         10.0},
      {   50.0,          0.0,          0.0,        -22.0},
      {    0.0,          7.0,          4.0,          0.0},
      {    0.0,          3.0,          1.0,          0.0},
      {   -4.0,          4.0,          2.0,          2.0},
      {   -5.0,        -11.0,         -5.0,          2.0},
      {    0.0,          4.0,          2.0,          0.0},
      {    4.0,         17.0,          9.0,         -2.0},
      {   59.0,          0.0,          0.0,          0.0},
      {    0.0,         -4.0,         -2.0,          0.0},
      {   -8.0,          0.0,          0.0,          4.0},
      {   -3.0,          0.0,          0.0,          0.0},
      {    4.0,        -15.0,         -8.0,         -2.0},
      {  370.0,         -8.0,          0.0,       -160.0},
      {    0.0,          0.0,         -3.0,          0.0},
      {    0.0,          3.0,          1.0,          0.0},
      {   -6.0,          3.0,          1.0,          3.0},
      {    0.0,          6.0,          0.0,          0.0},
      {  -10.0,          0.0,          0.0,          4.0},
      {    0.0,          9.0,          4.0,          0.0},
      {    4.0,         17.0,          7.0,         -2.0},
      {   34.0,          0.0,          0.0,        -15.0},
      {    0.0,          5.0,          3.0,          0.0},
      {   -5.0,          0.0,          0.0,          2.0},
      {  -37.0,         -7.0,         -3.0,         16.0},
      {    3.0,         13.0,          7.0,         -2.0},
      {   40.0,          0.0,          0.0,          0.0},
      {    0.0,         -3.0,         -2.0,          0.0},
      { -184.0,         -3.0,         -1.0,         80.0},
      {   -3.0,          0.0,          0.0,          1.0},
      {   -3.0,          0.0,          0.0,          0.0},
      {    0.0,        -10.0,         -6.0,         -1.0},
      {   31.0,         -6.0,          0.0,        -13.0},
      {   -3.0,        -32.0,        -14.0,          1.0},
      {   -7.0,          0.0,          0.0,          3.0},
      {    0.0,         -8.0,         -4.0,          0.0},
      {    3.0,         -4.0,          0.0,          0.0},
      {    0.0,          4.0,          0.0,          0.0},
      {    0.0,          3.0,          1.0,          0.0},
      {   19.0,        -23.0,        -10.0,          2.0},
      {    0.0,          0.0,          0.0,        -10.0},
      {    0.0,          3.0,          2.0,          0.0},
      {    0.0,          9.0,          5.0,         -1.0},
      {   28.0,          0.0,          0.0,          0.0},
      {    0.0,         -7.0,         -4.0,          0.0},
      {    8.0,         -4.0,          0.0,         -4.0},
      {    0.0,          0.0,         -2.0,          0.0},
      {    0.0,          3.0,          0.0,          0.0},
      {   -3.0,          0.0,          0.0,          1.0},
      {   -9.0,          0.0,          1.0,          4.0},
      {    3.0,         12.0,          5.0,         -1.0},
      {   17.0,         -3.0,         -1.0,          0.0},
      {    0.0,          7.0,          4.0,          0.0},
      {   19.0,          0.0,          0.0,          0.0},
      {    0.0,         -5.0,         -3.0,          0.0},
      {   14.0,         -3.0,          0.0,         -1.0},
      {    0.0,          0.0,         -1.0,          0.0},
      {    0.0,          0.0,          0.0,         -5.0},
      {    0.0,          5.0,          3.0,          0.0},
      {   13.0,          0.0,          0.0,          0.0},
      {    0.0,         -3.0,         -2.0,          0.0},
      {    2.0,          9.0,          4.0,          3.0},
      {    0.0,          0.0,          0.0,         -4.0},
      {    8.0,          0.0,          0.0,          0.0},
      {    0.0,          4.0,          2.0,          0.0},
      {    6.0,          0.0,          0.0,         -3.0},
      {    6.0,          0.0,          0.0,          0.0},
      {    0.0,          3.0,          1.0,          0.0},
      {    5.0,          0.0,          0.0,         -2.0},
      {    3.0,          0.0,          0.0,         -1.0},
      {   -3.0,          0.0,          0.0,          0.0},
      {    6.0,          0.0,          0.0,          0.0},
      {    7.0,          0.0,          0.0,          0.0},
      {   -4.0,          0.0,          0.0,          0.0},
      {    4.0,          0.0,          0.0,          0.0},
      {    6.0,          0.0,          0.0,          0.0},
      {    0.0,         -4.0,          0.0,          0.0},
      {    0.0,         -4.0,          0.0,          0.0},
      {    5.0,          0.0,          0.0,          0.0},
      {   -3.0,          0.0,          0.0,          0.0},
      {    4.0,          0.0,          0.0,          0.0},
      {   -5.0,          0.0,          0.0,          0.0},
      {    4.0,          0.0,          0.0,          0.0},
      {    0.0,          3.0,          0.0,          0.0},
      {   13.0,          0.0,          0.0,          0.0},
      {   21.0,         11.0,          0.0,          0.0},
      {    0.0,         -5.0,          0.0,          0.0},
      {    0.0,         -5.0,         -2.0,          0.0},
      {    0.0,          5.0,          3.0,          0.0},
      {    0.0,         -5.0,          0.0,          0.0},
      {   -3.0,          0.0,          0.0,          2.0},
      {   20.0,         10.0,          0.0,          0.0},
      {  -34.0,          0.0,          0.0,          0.0},
      {  -19.0,          0.0,          0.0,          0.0},
      {    3.0,          0.0,          0.0,         -2.0},
      {   -3.0,          0.0,          0.0,          1.0},
      {   -6.0,          0.0,          0.0,          3.0},
      {   -4.0,          0.0,          0.0,          0.0},
      {    3.0,          0.0,          0.0,          0.0},
      {    3.0,          0.0,          0.0,          0.0},
      {    4.0,          0.0,          0.0,          0.0},
      {    3.0,          0.0,          0.0,         -1.0},
      {    6.0,          0.0,          0.0,         -3.0},
      {   -8.0,          0.0,          0.0,          3.0},
      {    0.0,          3.0,          1.0,          0.0},
      {   -3.0,          0.0,          0.0,          0.0},
      {    0.0,         -3.0,         -2.0,          0.0},
      {  126.0,        -63.0,        -27.0,        -55.0},
      {   -5.0,          0.0,          1.0,          2.0},
      {   -3.0,         28.0,         15.0,          2.0},
      {    5.0,          0.0,          1.0,         -2.0},
      {    0.0,          9.0,          4.0,          1.0},
      {    0.0,          9.0,          4.0,         -1.0},
      { -126.0,        -63.0,        -27.0,         55.0},
      {    3.0,          0.0,          0.0,         -1.0},
      {   21.0,        -11.0,         -6.0,        -11.0},
      {    0.0,         -4.0,          0.0,          0.0},
      {  -21.0,        -11.0,         -6.0,         11.0},
      {   -3.0,          0.0,          0.0,          1.0},
      {    0.0,          3.0,          1.0,          0.0},
      {    8.0,          0.0,          0.0,         -4.0},
      {   -6.0,          0.0,          0.0,          3.0},
      {   -3.0,          0.0,          0.0,          1.0},
      {    3.0,          0.0,          0.0,         -1.0},
      {   -3.0,          0.0,          0.0,          1.0},
      {   -5.0,          0.0,          0.0,          2.0},
      {   24.0,        -12.0,         -5.0,        -11.0},
      {    0.0,          3.0,          1.0,          0.0},
      {    0.0,          3.0,          1.0,          0.0},
      {    0.0,          3.0,          2.0,          0.0},
      {  -24.0,        -12.0,         -5.0,         10.0},
      {    4.0,          0.0,         -1.0,         -2.0},
      {   13.0,          0.0,          0.0,         -6.0},
      {    7.0,          0.0,          0.0,         -3.0},
      {    3.0,          0.0,          0.0,         -1.0},
      {    3.0,          0.0,          0.0,         -1.0}};

/*
   Interval between fundamental epoch J2000.0 and given date.
*/

   t = ((jd_high - T0) + jd_low) / 36525.0;

/*
   Compute fundamental arguments from Simon et al. (1994), in radians.
*/

   fund_args (t, a);

/*
   ** Luni-solar nutation. **
*/

/*
   Initialize the nutation values.
*/

   dp = 0.0;
   de = 0.0;

/*
   Summation of luni-solar nutation series (in reverse order).
*/

   for (i = 677; i >= 0; i--)
   {

/*
   Argument and functions.
*/

      arg = fmod ((double) nals_t[i][0] * a[0]  +
                  (double) nals_t[i][1] * a[1]  +
                  (double) nals_t[i][2] * a[2]  +
                  (double) nals_t[i][3] * a[3]  +
                  (double) nals_t[i][4] * a[4], TWOPI);

      sarg = sin (arg);
      carg = cos (arg);

/*
   Term.
*/

      dp += (cls_t[i][0] + cls_t[i][1] * t) * sarg
              +   cls_t[i][2] * carg;
      de += (cls_t[i][3] + cls_t[i][4] * t) * carg
              +   cls_t[i][5] * sarg;
   }

/*
   Convert from 0.1 microarcsec units to radians.
*/

   factor = 1.0e-7 * ASEC2RAD;
   dpsils = dp * factor;
   depsls = de * factor;

/*
   ** Planetary nutation. **
*/

/*
   Mean anomaly of the Moon.
*/

   al = fmod (2.35555598 + 8328.6914269554 * t, TWOPI);

/*
   Mean anomaly of the Sun.
*/

   alsu = fmod (6.24006013 + 628.301955 * t, TWOPI);

/*
   Mean argument of the latitude of the Moon.
*/

   af = fmod (1.627905234 + 8433.466158131 * t, TWOPI);

/*
   Mean elongation of the Moon from the Sun.
*/

   ad = fmod (5.198466741 + 7771.3771468121 * t, TWOPI);

/*
   Mean longitude of the ascending node of the Moon.
*/

   aom = fmod (2.18243920 - 33.757045 * t, TWOPI);

/*
   General accumulated precession in longitude.
*/

   apa = (0.02438175 + 0.00000538691 * t) * t;
/*
   Planetary longitudes, Mercury through Neptune (Souchay et al. 1999).
*/

   alme = fmod (4.402608842 + 2608.7903141574 * t, TWOPI);
   alve = fmod (3.176146697 + 1021.3285546211 * t, TWOPI);
   alea = fmod (1.753470314 +  628.3075849991 * t, TWOPI);
   alma = fmod (6.203480913 +  334.0612426700 * t, TWOPI);
   alju = fmod (0.599546497 +   52.9690962641 * t, TWOPI);
   alsa = fmod (0.874016757 +   21.3299104960 * t, TWOPI);
   alur = fmod (5.481293871 +    7.4781598567 * t, TWOPI);
   alne = fmod (5.321159000 +    3.8127774000 * t, TWOPI);

/*
   Initialize the nutation values.
*/

   dp = 0.0;
   de = 0.0;

/*
   Summation of planetary nutation series (in reverse order).
*/

   for (i = 686; i >= 0; i--)
   {

/*
   Argument and functions.
*/

      arg = fmod ((double) napl_t[i][ 0] * al    +
                  (double) napl_t[i][ 1] * alsu  +
                  (double) napl_t[i][ 2] * af    +
                  (double) napl_t[i][ 3] * ad    +
                  (double) napl_t[i][ 4] * aom   +
                  (double) napl_t[i][ 5] * alme  +
                  (double) napl_t[i][ 6] * alve  +
                  (double) napl_t[i][ 7] * alea  +
                  (double) napl_t[i][ 8] * alma  +
                  (double) napl_t[i][ 9] * alju  +
                  (double) napl_t[i][10] * alsa  +
                  (double) napl_t[i][11] * alur  +
                  (double) napl_t[i][12] * alne  +
                  (double) napl_t[i][13] * apa, TWOPI);

      sarg = sin (arg);
      carg = cos (arg);

/*
   Term.
*/

      dp += cpl_t[i][0] * sarg + cpl_t[i][1] * carg;
      de += cpl_t[i][2] * sarg + cpl_t[i][3] * carg;
   }

   dpsipl = dp * factor;
   depspl = de * factor;

/*
   Total: Add planetary and luni-solar components.
*/

   *dpsi = dpsipl + dpsils;
   *deps = depspl + depsls;

   return;
}

/********iau2000b */

void iau2000b (double jd_high, double jd_low,

               double *dpsi, double *deps)
/*
------------------------------------------------------------------------

   PURPOSE:
      To compute the forced nutation of the non-rigid Earth based on
      the IAU 2000B precession/nutation model.

   REFERENCES:
      McCarthy, D. and Luzum, B. (2003). "An Abridged Model of the
         Precession & Nutation of the Celestial Pole," Celestial
         Mechanics and Dynamical Astronomy, Volume 85, Issue 1,
         Jan. 2003, p. 37. (IAU 2000B)
      IERS Conventions (2003), Chapter 5.

   INPUT
   ARGUMENTS:
      jd_high (double)
         High-order part of TT Julian date.
      jd_low (double)
         Low-order part of TT Julian date.

   OUTPUT
   ARGUMENTS:
      *dpsi (double)
         Nutation (luni-solar + planetary) in longitude, in radians.
      *deps (double)
         Nutation (luni-solar + planetary) in obliquity, in radians.

   RETURNED
   VALUE:
      None.

   GLOBALS
   USED:
      T0, ASEC2RAD, TWOPI

   FUNCTIONS
   CALLED:
      fmod      math.h
      sin       math.h
      cos       math.h

   VER./DATE/
   PROGRAMMER:
      V1.0/09-03/JAB (USNO/AA)
      V1.1/12-10/JAB (USNO/AA): Implement static storage class for const
                                arrays.
      V1.2/03-11/WKP (USNO/AA): Added braces to 2-D array initialization
                                to quiet gcc warnings.

   NOTES:
      1. IAU 2000B reproduces the IAU 2000A model to a precision of
      1 milliarcsecond in the interval 1995-2020.

------------------------------------------------------------------------
*/
{
   short int i;

/*
   Planetary nutation (arcsec).  These fixed terms account for the
   omission of the long-period planetary terms in the truncated model.
*/

   double dpplan = -0.000135;
   double deplan =  0.000388;

   double t, el, elp, f, d, om, arg, dp, de, sarg, carg, factor, dpsils,
      depsls, dpsipl, depspl;

/*
   Luni-Solar argument multipliers:
       L     L'    F     D     Om
*/

   static const short int nals_t[77][5] = {
      { 0,    0,    0,    0,    1},
      { 0,    0,    2,   -2,    2},
      { 0,    0,    2,    0,    2},
      { 0,    0,    0,    0,    2},
      { 0,    1,    0,    0,    0},
      { 0,    1,    2,   -2,    2},
      { 1,    0,    0,    0,    0},
      { 0,    0,    2,    0,    1},
      { 1,    0,    2,    0,    2},
      { 0,   -1,    2,   -2,    2},
      { 0,    0,    2,   -2,    1},
      {-1,    0,    2,    0,    2},
      {-1,    0,    0,    2,    0},
      { 1,    0,    0,    0,    1},
      {-1,    0,    0,    0,    1},
      {-1,    0,    2,    2,    2},
      { 1,    0,    2,    0,    1},
      {-2,    0,    2,    0,    1},
      { 0,    0,    0,    2,    0},
      { 0,    0,    2,    2,    2},
      { 0,   -2,    2,   -2,    2},
      {-2,    0,    0,    2,    0},
      { 2,    0,    2,    0,    2},
      { 1,    0,    2,   -2,    2},
      {-1,    0,    2,    0,    1},
      { 2,    0,    0,    0,    0},
      { 0,    0,    2,    0,    0},
      { 0,    1,    0,    0,    1},
      {-1,    0,    0,    2,    1},
      { 0,    2,    2,   -2,    2},
      { 0,    0,   -2,    2,    0},
      { 1,    0,    0,   -2,    1},
      { 0,   -1,    0,    0,    1},
      {-1,    0,    2,    2,    1},
      { 0,    2,    0,    0,    0},
      { 1,    0,    2,    2,    2},
      {-2,    0,    2,    0,    0},
      { 0,    1,    2,    0,    2},
      { 0,    0,    2,    2,    1},
      { 0,   -1,    2,    0,    2},
      { 0,    0,    0,    2,    1},
      { 1,    0,    2,   -2,    1},
      { 2,    0,    2,   -2,    2},
      {-2,    0,    0,    2,    1},
      { 2,    0,    2,    0,    1},
      { 0,   -1,    2,   -2,    1},
      { 0,    0,    0,   -2,    1},
      {-1,   -1,    0,    2,    0},
      { 2,    0,    0,   -2,    1},
      { 1,    0,    0,    2,    0},
      { 0,    1,    2,   -2,    1},
      { 1,   -1,    0,    0,    0},
      {-2,    0,    2,    0,    2},
      { 3,    0,    2,    0,    2},
      { 0,   -1,    0,    2,    0},
      { 1,   -1,    2,    0,    2},
      { 0,    0,    0,    1,    0},
      {-1,   -1,    2,    2,    2},
      {-1,    0,    2,    0,    0},
      { 0,   -1,    2,    2,    2},
      {-2,    0,    0,    0,    1},
      { 1,    1,    2,    0,    2},
      { 2,    0,    0,    0,    1},
      {-1,    1,    0,    1,    0},
      { 1,    1,    0,    0,    0},
      { 1,    0,    2,    0,    0},
      {-1,    0,    2,   -2,    1},
      { 1,    0,    0,    0,    2},
      {-1,    0,    0,    1,    0},
      { 0,    0,    2,    1,    2},
      {-1,    0,    2,    4,    2},
      {-1,    1,    0,    1,    1},
      { 0,   -2,    2,   -2,    1},
      { 1,    0,    2,    2,    1},
      {-2,    0,    2,    2,    2},
      {-1,    0,    0,    0,    2},
      { 1,    1,    2,   -2,    2}};

/*
   Luni-Solar nutation coefficients, unit 1e-7 arcsec:
   longitude (sin, t*sin, cos), obliquity (cos, t*cos, sin)

   Each row of coefficients in 'cls_t' belongs with the corresponding
   row of fundamental-argument multipliers in 'nals_t'.
*/

   static const double cls_t[77][6] = {
      {-172064161.0, -174666.0,  33386.0, 92052331.0,  9086.0, 15377.0},
      { -13170906.0,   -1675.0, -13696.0,  5730336.0, -3015.0, -4587.0},
      {  -2276413.0,    -234.0,   2796.0,   978459.0,  -485.0,  1374.0},
      {   2074554.0,     207.0,   -698.0,  -897492.0,   470.0,  -291.0},
      {   1475877.0,   -3633.0,  11817.0,    73871.0,  -184.0, -1924.0},
      {   -516821.0,    1226.0,   -524.0,   224386.0,  -677.0,  -174.0},
      {    711159.0,      73.0,   -872.0,    -6750.0,     0.0,   358.0},
      {   -387298.0,    -367.0,    380.0,   200728.0,    18.0,   318.0},
      {   -301461.0,     -36.0,    816.0,   129025.0,   -63.0,   367.0},
      {    215829.0,    -494.0,    111.0,   -95929.0,   299.0,   132.0},
      {    128227.0,     137.0,    181.0,   -68982.0,    -9.0,    39.0},
      {    123457.0,      11.0,     19.0,   -53311.0,    32.0,    -4.0},
      {    156994.0,      10.0,   -168.0,    -1235.0,     0.0,    82.0},
      {     63110.0,      63.0,     27.0,   -33228.0,     0.0,    -9.0},
      {    -57976.0,     -63.0,   -189.0,    31429.0,     0.0,   -75.0},
      {    -59641.0,     -11.0,    149.0,    25543.0,   -11.0,    66.0},
      {    -51613.0,     -42.0,    129.0,    26366.0,     0.0,    78.0},
      {     45893.0,      50.0,     31.0,   -24236.0,   -10.0,    20.0},
      {     63384.0,      11.0,   -150.0,    -1220.0,     0.0,    29.0},
      {    -38571.0,      -1.0,    158.0,    16452.0,   -11.0,    68.0},
      {     32481.0,       0.0,      0.0,   -13870.0,     0.0,     0.0},
      {    -47722.0,       0.0,    -18.0,      477.0,     0.0,   -25.0},
      {    -31046.0,      -1.0,    131.0,    13238.0,   -11.0,    59.0},
      {     28593.0,       0.0,     -1.0,   -12338.0,    10.0,    -3.0},
      {     20441.0,      21.0,     10.0,   -10758.0,     0.0,    -3.0},
      {     29243.0,       0.0,    -74.0,     -609.0,     0.0,    13.0},
      {     25887.0,       0.0,    -66.0,     -550.0,     0.0,    11.0},
      {    -14053.0,     -25.0,     79.0,     8551.0,    -2.0,   -45.0},
      {     15164.0,      10.0,     11.0,    -8001.0,     0.0,    -1.0},
      {    -15794.0,      72.0,    -16.0,     6850.0,   -42.0,    -5.0},
      {     21783.0,       0.0,     13.0,     -167.0,     0.0,    13.0},
      {    -12873.0,     -10.0,    -37.0,     6953.0,     0.0,   -14.0},
      {    -12654.0,      11.0,     63.0,     6415.0,     0.0,    26.0},
      {    -10204.0,       0.0,     25.0,     5222.0,     0.0,    15.0},
      {     16707.0,     -85.0,    -10.0,      168.0,    -1.0,    10.0},
      {     -7691.0,       0.0,     44.0,     3268.0,     0.0,    19.0},
      {    -11024.0,       0.0,    -14.0,      104.0,     0.0,     2.0},
      {      7566.0,     -21.0,    -11.0,    -3250.0,     0.0,    -5.0},
      {     -6637.0,     -11.0,     25.0,     3353.0,     0.0,    14.0},
      {     -7141.0,      21.0,      8.0,     3070.0,     0.0,     4.0},
      {     -6302.0,     -11.0,      2.0,     3272.0,     0.0,     4.0},
      {      5800.0,      10.0,      2.0,    -3045.0,     0.0,    -1.0},
      {      6443.0,       0.0,     -7.0,    -2768.0,     0.0,    -4.0},
      {     -5774.0,     -11.0,    -15.0,     3041.0,     0.0,    -5.0},
      {     -5350.0,       0.0,     21.0,     2695.0,     0.0,    12.0},
      {     -4752.0,     -11.0,     -3.0,     2719.0,     0.0,    -3.0},
      {     -4940.0,     -11.0,    -21.0,     2720.0,     0.0,    -9.0},
      {      7350.0,       0.0,     -8.0,      -51.0,     0.0,     4.0},
      {      4065.0,       0.0,      6.0,    -2206.0,     0.0,     1.0},
      {      6579.0,       0.0,    -24.0,     -199.0,     0.0,     2.0},
      {      3579.0,       0.0,      5.0,    -1900.0,     0.0,     1.0},
      {      4725.0,       0.0,     -6.0,      -41.0,     0.0,     3.0},
      {     -3075.0,       0.0,     -2.0,     1313.0,     0.0,    -1.0},
      {     -2904.0,       0.0,     15.0,     1233.0,     0.0,     7.0},
      {      4348.0,       0.0,    -10.0,      -81.0,     0.0,     2.0},
      {     -2878.0,       0.0,      8.0,     1232.0,     0.0,     4.0},
      {     -4230.0,       0.0,      5.0,      -20.0,     0.0,    -2.0},
      {     -2819.0,       0.0,      7.0,     1207.0,     0.0,     3.0},
      {     -4056.0,       0.0,      5.0,       40.0,     0.0,    -2.0},
      {     -2647.0,       0.0,     11.0,     1129.0,     0.0,     5.0},
      {     -2294.0,       0.0,    -10.0,     1266.0,     0.0,    -4.0},
      {      2481.0,       0.0,     -7.0,    -1062.0,     0.0,    -3.0},
      {      2179.0,       0.0,     -2.0,    -1129.0,     0.0,    -2.0},
      {      3276.0,       0.0,      1.0,       -9.0,     0.0,     0.0},
      {     -3389.0,       0.0,      5.0,       35.0,     0.0,    -2.0},
      {      3339.0,       0.0,    -13.0,     -107.0,     0.0,     1.0},
      {     -1987.0,       0.0,     -6.0,     1073.0,     0.0,    -2.0},
      {     -1981.0,       0.0,      0.0,      854.0,     0.0,     0.0},
      {      4026.0,       0.0,   -353.0,     -553.0,     0.0,  -139.0},
      {      1660.0,       0.0,     -5.0,     -710.0,     0.0,    -2.0},
      {     -1521.0,       0.0,      9.0,      647.0,     0.0,     4.0},
      {      1314.0,       0.0,      0.0,     -700.0,     0.0,     0.0},
      {     -1283.0,       0.0,      0.0,      672.0,     0.0,     0.0},
      {     -1331.0,       0.0,      8.0,      663.0,     0.0,     4.0},
      {      1383.0,       0.0,     -2.0,     -594.0,     0.0,    -2.0},
      {      1405.0,       0.0,      4.0,     -610.0,     0.0,     2.0},
      {      1290.0,       0.0,      0.0,     -556.0,     0.0,     0.0}};

/*
   Interval between fundamental epoch J2000.0 and given date.
*/

   t = ((jd_high - T0) + jd_low) / 36525.0;

/*
   ** Luni-solar nutation. **

   Fundamental (Delaunay) arguments from Simon et al. (1994),
   in radians.
*/

/*
   Mean anomaly of the Moon.
*/

   el  = fmod (485868.249036 +
          t * 1717915923.2178, ASEC360) * ASEC2RAD;

/*
   Mean anomaly of the Sun.
*/

   elp = fmod (1287104.79305 +
             t * 129596581.0481, ASEC360) * ASEC2RAD;

/*
   Mean argument of the latitude of the Moon.
*/

   f   = fmod (335779.526232 +
             t * 1739527262.8478, ASEC360) * ASEC2RAD;

/*
   Mean elongation of the Moon from the Sun.
*/

   d   = fmod (1072260.70369 +
             t * 1602961601.2090, ASEC360) * ASEC2RAD;

/*
   Mean longitude of the ascending node of the Moon.
*/

   om  = fmod (450160.398036 -
             t * 6962890.5431, ASEC360) * ASEC2RAD;

/*
  Initialize the nutation values.
*/

   dp = 0.0;
   de = 0.0;

/*
  Summation of luni-solar nutation series (in reverse order).
*/

   for (i = 76; i >= 0; i--)
   {

/*
   Argument and functions.
*/

      arg = fmod ((double) nals_t[i][0] * el  +
                  (double) nals_t[i][1] * elp +
                  (double) nals_t[i][2] * f   +
                  (double) nals_t[i][3] * d   +
                  (double) nals_t[i][4] * om,   TWOPI);

      sarg = sin (arg);
      carg = cos (arg);

/*
   Term.
*/

      dp += (cls_t[i][0] + cls_t[i][1] * t) * sarg
              +   cls_t[i][2] * carg;
      de += (cls_t[i][3] + cls_t[i][4] * t) * carg
              +   cls_t[i][5] * sarg;
   }

/*
  Convert from 0.1 microarcsec units to radians.
*/

   factor = 1.0e-7 * ASEC2RAD;
   dpsils = dp * factor;
   depsls = de * factor;

/*
  ** Planetary nutation. **

  Fixed terms to allow for long-period nutation, in radians.
*/

   dpsipl = dpplan * ASEC2RAD;
   depspl = deplan * ASEC2RAD;

/*
   Total: Add planetary and luni-solar components.
*/

   *dpsi = dpsipl + dpsils;
   *deps = depspl + depsls;

   return;
}

/********nu2000k */

void nu2000k (double jd_high, double jd_low,

              double *dpsi, double *deps)
/*
------------------------------------------------------------------------

   PURPOSE:
      To compute the forced nutation of the non-rigid Earth:
      Model NU2000K.  This model is a modified version of IAU 2000A,
      which has been truncated for speed of execution, and uses Simon
      et al. (1994) fundamental arguments throughout.  NU2000K agrees
      with IAU 2000A at the 0.1 milliarcsecond level from 1700 to
      2300.

   REFERENCES:
      IERS Conventions (2003), Chapter 5.
      Simon et al. (1994) Astronomy and Astrophysics 282, 663-683,
         esp. Sections 3.4-3.5.

   INPUT
   ARGUMENTS:
      jd_high (double)
         High-order part of TT Julian date.
      jd_low (double)
         Low-order part of TT Julian date.

   OUTPUT
   ARGUMENTS:
      *dpsi (double)
         Nutation (luni-solar + planetary) in longitude, in radians.
      *deps (double)
         Nutation (luni-solar + planetary) in obliquity, in radians.

   RETURNED
   VALUE:
      None.

   GLOBALS
   USED:
      T0, ASEC2RAD, TWOPI

   FUNCTIONS
   CALLED:
      fund_args    novas.c
      fmod         math.h
      sin          math.h
      cos          math.h

   VER./DATE/
   PROGRAMMER:
      V1.0/03-04/JAB (USNO/AA)
      V1.1/12-10/JAB (USNO/AA): Implement static storage class for const
                                arrays.
      V1.2/03-11/WKP (USNO/AA): Added braces to 2-D array initialization
                                to quiet gcc warnings.

   NOTES:
      1. NU2000K was compared to IAU 2000A over six centuries (1700-
      2300).  The average error in dpsi is 20 microarcseconds, with 98%
      of the errors < 60 microarcseconds;  the average error in deleps
      is 8 microarcseconds, with 100% of the errors < 60
      microarcseconds.
     2. NU2000K was developed by G. Kaplan (USNO) in March 2004.
     3. This function is the "C" version of NOVAS Fortran routine
      'nu2000k'.

------------------------------------------------------------------------
*/
{
   short int i;

   double t, a[5], dp, de, arg, sarg, carg, factor, dpsils,
      depsls, alme, alve, alea, alma, alju, alsa, alur, alne, apa,
      dpsipl, depspl;

/*
   Luni-Solar argument multipliers:
       L     L'    F     D     Om
*/

   static const short int nals_t[323][5] = {
      { 0,    0,    0,    0,    1},
      { 0,    0,    2,   -2,    2},
      { 0,    0,    2,    0,    2},
      { 0,    0,    0,    0,    2},
      { 0,    1,    0,    0,    0},
      { 0,    1,    2,   -2,    2},
      { 1,    0,    0,    0,    0},
      { 0,    0,    2,    0,    1},
      { 1,    0,    2,    0,    2},
      { 0,   -1,    2,   -2,    2},
      { 0,    0,    2,   -2,    1},
      {-1,    0,    2,    0,    2},
      {-1,    0,    0,    2,    0},
      { 1,    0,    0,    0,    1},
      {-1,    0,    0,    0,    1},
      {-1,    0,    2,    2,    2},
      { 1,    0,    2,    0,    1},
      {-2,    0,    2,    0,    1},
      { 0,    0,    0,    2,    0},
      { 0,    0,    2,    2,    2},
      { 0,   -2,    2,   -2,    2},
      {-2,    0,    0,    2,    0},
      { 2,    0,    2,    0,    2},
      { 1,    0,    2,   -2,    2},
      {-1,    0,    2,    0,    1},
      { 2,    0,    0,    0,    0},
      { 0,    0,    2,    0,    0},
      { 0,    1,    0,    0,    1},
      {-1,    0,    0,    2,    1},
      { 0,    2,    2,   -2,    2},
      { 0,    0,   -2,    2,    0},
      { 1,    0,    0,   -2,    1},
      { 0,   -1,    0,    0,    1},
      {-1,    0,    2,    2,    1},
      { 0,    2,    0,    0,    0},
      { 1,    0,    2,    2,    2},
      {-2,    0,    2,    0,    0},
      { 0,    1,    2,    0,    2},
      { 0,    0,    2,    2,    1},
      { 0,   -1,    2,    0,    2},
      { 0,    0,    0,    2,    1},
      { 1,    0,    2,   -2,    1},
      { 2,    0,    2,   -2,    2},
      {-2,    0,    0,    2,    1},
      { 2,    0,    2,    0,    1},
      { 0,   -1,    2,   -2,    1},
      { 0,    0,    0,   -2,    1},
      {-1,   -1,    0,    2,    0},
      { 2,    0,    0,   -2,    1},
      { 1,    0,    0,    2,    0},
      { 0,    1,    2,   -2,    1},
      { 1,   -1,    0,    0,    0},
      {-2,    0,    2,    0,    2},
      { 3,    0,    2,    0,    2},
      { 0,   -1,    0,    2,    0},
      { 1,   -1,    2,    0,    2},
      { 0,    0,    0,    1,    0},
      {-1,   -1,    2,    2,    2},
      {-1,    0,    2,    0,    0},
      { 0,   -1,    2,    2,    2},
      {-2,    0,    0,    0,    1},
      { 1,    1,    2,    0,    2},
      { 2,    0,    0,    0,    1},
      {-1,    1,    0,    1,    0},
      { 1,    1,    0,    0,    0},
      { 1,    0,    2,    0,    0},
      {-1,    0,    2,   -2,    1},
      { 1,    0,    0,    0,    2},
      {-1,    0,    0,    1,    0},
      { 0,    0,    2,    1,    2},
      {-1,    0,    2,    4,    2},
      {-1,    1,    0,    1,    1},
      { 0,   -2,    2,   -2,    1},
      { 1,    0,    2,    2,    1},
      {-2,    0,    2,    2,    2},
      {-1,    0,    0,    0,    2},
      { 1,    1,    2,   -2,    2},
      {-2,    0,    2,    4,    2},
      {-1,    0,    4,    0,    2},
      { 2,    0,    2,   -2,    1},
      { 2,    0,    2,    2,    2},
      { 1,    0,    0,    2,    1},
      { 3,    0,    0,    0,    0},
      { 3,    0,    2,   -2,    2},
      { 0,    0,    4,   -2,    2},
      { 0,    1,    2,    0,    1},
      { 0,    0,   -2,    2,    1},
      { 0,    0,    2,   -2,    3},
      {-1,    0,    0,    4,    0},
      { 2,    0,   -2,    0,    1},
      {-2,    0,    0,    4,    0},
      {-1,   -1,    0,    2,    1},
      {-1,    0,    0,    1,    1},
      { 0,    1,    0,    0,    2},
      { 0,    0,   -2,    0,    1},
      { 0,   -1,    2,    0,    1},
      { 0,    0,    2,   -1,    2},
      { 0,    0,    2,    4,    2},
      {-2,   -1,    0,    2,    0},
      { 1,    1,    0,   -2,    1},
      {-1,    1,    0,    2,    0},
      {-1,    1,    0,    1,    2},
      { 1,   -1,    0,    0,    1},
      { 1,   -1,    2,    2,    2},
      {-1,    1,    2,    2,    2},
      { 3,    0,    2,    0,    1},
      { 0,    1,   -2,    2,    0},
      {-1,    0,    0,   -2,    1},
      { 0,    1,    2,    2,    2},
      {-1,   -1,    2,    2,    1},
      { 0,   -1,    0,    0,    2},
      { 1,    0,    2,   -4,    1},
      {-1,    0,   -2,    2,    0},
      { 0,   -1,    2,    2,    1},
      { 2,   -1,    2,    0,    2},
      { 0,    0,    0,    2,    2},
      { 1,   -1,    2,    0,    1},
      {-1,    1,    2,    0,    2},
      { 0,    1,    0,    2,    0},
      { 0,   -1,   -2,    2,    0},
      { 0,    3,    2,   -2,    2},
      { 0,    0,    0,    1,    1},
      {-1,    0,    2,    2,    0},
      { 2,    1,    2,    0,    2},
      { 1,    1,    0,    0,    1},
      { 1,    1,    2,    0,    1},
      { 2,    0,    0,    2,    0},
      { 1,    0,   -2,    2,    0},
      {-1,    0,    0,    2,    2},
      { 0,    1,    0,    1,    0},
      { 0,    1,    0,   -2,    1},
      {-1,    0,    2,   -2,    2},
      { 0,    0,    0,   -1,    1},
      {-1,    1,    0,    0,    1},
      { 1,    0,    2,   -1,    2},
      { 1,   -1,    0,    2,    0},
      { 0,    0,    0,    4,    0},
      { 1,    0,    2,    1,    2},
      { 0,    0,    2,    1,    1},
      { 1,    0,    0,   -2,    2},
      {-1,    0,    2,    4,    1},
      { 1,    0,   -2,    0,    1},
      { 1,    1,    2,   -2,    1},
      { 0,    0,    2,    2,    0},
      {-1,    0,    2,   -1,    1},
      {-2,    0,    2,    2,    1},
      { 4,    0,    2,    0,    2},
      { 2,   -1,    0,    0,    0},
      { 2,    1,    2,   -2,    2},
      { 0,    1,    2,    1,    2},
      { 1,    0,    4,   -2,    2},
      {-1,   -1,    0,    0,    1},
      { 0,    1,    0,    2,    1},
      {-2,    0,    2,    4,    1},
      { 2,    0,    2,    0,    0},
      { 1,    0,    0,    1,    0},
      {-1,    0,    0,    4,    1},
      {-1,    0,    4,    0,    1},
      { 2,    0,    2,    2,    1},
      { 0,    0,    2,   -3,    2},
      {-1,   -2,    0,    2,    0},
      { 2,    1,    0,    0,    0},
      { 0,    0,    4,    0,    2},
      { 0,    0,    0,    0,    3},
      { 0,    3,    0,    0,    0},
      { 0,    0,    2,   -4,    1},
      { 0,   -1,    0,    2,    1},
      { 0,    0,    0,    4,    1},
      {-1,   -1,    2,    4,    2},
      { 1,    0,    2,    4,    2},
      {-2,    2,    0,    2,    0},
      {-2,   -1,    2,    0,    1},
      {-2,    0,    0,    2,    2},
      {-1,   -1,    2,    0,    2},
      { 0,    0,    4,   -2,    1},
      { 3,    0,    2,   -2,    1},
      {-2,   -1,    0,    2,    1},
      { 1,    0,    0,   -1,    1},
      { 0,   -2,    0,    2,    0},
      {-2,    0,    0,    4,    1},
      {-3,    0,    0,    0,    1},
      { 1,    1,    2,    2,    2},
      { 0,    0,    2,    4,    1},
      { 3,    0,    2,    2,    2},
      {-1,    1,    2,   -2,    1},
      { 2,    0,    0,   -4,    1},
      { 0,    0,    0,   -2,    2},
      { 2,    0,    2,   -4,    1},
      {-1,    1,    0,    2,    1},
      { 0,    0,    2,   -1,    1},
      { 0,   -2,    2,    2,    2},
      { 2,    0,    0,    2,    1},
      { 4,    0,    2,   -2,    2},
      { 2,    0,    0,   -2,    2},
      { 0,    2,    0,    0,    1},
      { 1,    0,    0,   -4,    1},
      { 0,    2,    2,   -2,    1},
      {-3,    0,    0,    4,    0},
      {-1,    1,    2,    0,    1},
      {-1,   -1,    0,    4,    0},
      {-1,   -2,    2,    2,    2},
      {-2,   -1,    2,    4,    2},
      { 1,   -1,    2,    2,    1},
      {-2,    1,    0,    2,    0},
      {-2,    1,    2,    0,    1},
      { 2,    1,    0,   -2,    1},
      {-3,    0,    2,    0,    1},
      {-2,    0,    2,   -2,    1},
      {-1,    1,    0,    2,    2},
      { 0,   -1,    2,   -1,    2},
      {-1,    0,    4,   -2,    2},
      { 0,   -2,    2,    0,    2},
      {-1,    0,    2,    1,    2},
      { 2,    0,    0,    0,    2},
      { 0,    0,    2,    0,    3},
      {-2,    0,    4,    0,    2},
      {-1,    0,   -2,    0,    1},
      {-1,    1,    2,    2,    1},
      { 3,    0,    0,    0,    1},
      {-1,    0,    2,    3,    2},
      { 2,   -1,    2,    0,    1},
      { 0,    1,    2,    2,    1},
      { 0,   -1,    2,    4,    2},
      { 2,   -1,    2,    2,    2},
      { 0,    2,   -2,    2,    0},
      {-1,   -1,    2,   -1,    1},
      { 0,   -2,    0,    0,    1},
      { 1,    0,    2,   -4,    2},
      { 1,   -1,    0,   -2,    1},
      {-1,   -1,    2,    0,    1},
      { 1,   -1,    2,   -2,    2},
      {-2,   -1,    0,    4,    0},
      {-1,    0,    0,    3,    0},
      {-2,   -1,    2,    2,    2},
      { 0,    2,    2,    0,    2},
      { 1,    1,    0,    2,    0},
      { 2,    0,    2,   -1,    2},
      { 1,    0,    2,    1,    1},
      { 4,    0,    0,    0,    0},
      { 2,    1,    2,    0,    1},
      { 3,   -1,    2,    0,    2},
      {-2,    2,    0,    2,    1},
      { 1,    0,    2,   -3,    1},
      { 1,    1,    2,   -4,    1},
      {-1,   -1,    2,   -2,    1},
      { 0,   -1,    0,   -1,    1},
      { 0,   -1,    0,   -2,    1},
      {-2,    0,    0,    0,    2},
      {-2,    0,   -2,    2,    0},
      {-1,    0,   -2,    4,    0},
      { 1,   -2,    0,    0,    0},
      { 0,    1,    0,    1,    1},
      {-1,    2,    0,    2,    0},
      { 1,   -1,    2,   -2,    1},
      { 1,    2,    2,   -2,    2},
      { 2,   -1,    2,   -2,    2},
      { 1,    0,    2,   -1,    1},
      { 2,    1,    2,   -2,    1},
      {-2,    0,    0,   -2,    1},
      { 1,   -2,    2,    0,    2},
      { 0,    1,    2,    1,    1},
      { 1,    0,    4,   -2,    1},
      {-2,    0,    4,    2,    2},
      { 1,    1,    2,    1,    2},
      { 1,    0,    0,    4,    0},
      { 1,    0,    2,    2,    0},
      { 2,    0,    2,    1,    2},
      { 3,    1,    2,    0,    2},
      { 4,    0,    2,    0,    1},
      {-2,   -1,    2,    0,    0},
      { 0,    1,   -2,    2,    1},
      { 1,    0,   -2,    1,    0},
      { 2,   -1,    0,   -2,    1},
      {-1,    0,    2,   -1,    2},
      { 1,    0,    2,   -3,    2},
      { 0,    1,    2,   -2,    3},
      {-1,    0,   -2,    2,    1},
      { 0,    0,    2,   -4,    2},
      { 2,    0,    2,   -4,    2},
      { 0,    0,    4,   -4,    4},
      { 0,    0,    4,   -4,    2},
      {-2,    0,    0,    3,    0},
      { 1,    0,   -2,    2,    1},
      {-3,    0,    2,    2,    2},
      {-2,    0,    2,    2,    0},
      { 2,   -1,    0,    0,    1},
      { 1,    1,    0,    1,    0},
      { 0,    1,    4,   -2,    2},
      {-1,    1,    0,   -2,    1},
      { 0,    0,    0,   -4,    1},
      { 1,   -1,    0,    2,    1},
      { 1,    1,    0,    2,    1},
      {-1,    2,    2,    2,    2},
      { 3,    1,    2,   -2,    2},
      { 0,   -1,    0,    4,    0},
      { 2,   -1,    0,    2,    0},
      { 0,    0,    4,    0,    1},
      { 2,    0,    4,   -2,    2},
      {-1,   -1,    2,    4,    1},
      { 1,    0,    0,    4,    1},
      { 1,   -2,    2,    2,    2},
      { 0,    0,    2,    3,    2},
      {-1,    1,    2,    4,    2},
      { 3,    0,    0,    2,    0},
      {-1,    0,    4,    2,    2},
      {-2,    0,    2,    6,    2},
      {-1,    0,    2,    6,    2},
      { 1,    1,   -2,    1,    0},
      {-1,    0,    0,    1,    2},
      {-1,   -1,    0,    1,    0},
      {-2,    0,    0,    1,    0},
      { 0,    0,   -2,    1,    0},
      { 1,   -1,   -2,    2,    0},
      { 1,    2,    0,    0,    0},
      { 3,    0,    2,    0,    0},
      { 0,   -1,    1,   -1,    1},
      {-1,    0,    1,    0,    3},
      {-1,    0,    1,    0,    2},
      {-1,    0,    1,    0,    1},
      {-1,    0,    1,    0,    0},
      { 0,    0,    1,    0,    2},
      { 0,    0,    1,    0,    1},
      { 0,    0,    1,    0,    0}};

/*
   Luni-Solar nutation coefficients, unit 1e-7 arcsec:
   longitude (sin, t*sin, cos), obliquity (cos, t*cos, sin)

   Each row of coefficients in 'cls_t' belongs with the corresponding
   row of fundamental-argument multipliers in 'nals_t'.
*/

   static const double cls_t[323][6] = {
      {-172064161.0,-174666.0, 33386.0, 92052331.0, 9086.0,15377.0},
      { -13170906.0,  -1675.0,-13696.0,  5730336.0,-3015.0,-4587.0},
      {  -2276413.0,   -234.0,  2796.0,   978459.0, -485.0, 1374.0},
      {   2074554.0,    207.0,  -698.0,  -897492.0,  470.0, -291.0},
      {   1475877.0,  -3633.0, 11817.0,    73871.0, -184.0,-1924.0},
      {   -516821.0,   1226.0,  -524.0,   224386.0, -677.0, -174.0},
      {    711159.0,     73.0,  -872.0,    -6750.0,    0.0,  358.0},
      {   -387298.0,   -367.0,   380.0,   200728.0,   18.0,  318.0},
      {   -301461.0,    -36.0,   816.0,   129025.0,  -63.0,  367.0},
      {    215829.0,   -494.0,   111.0,   -95929.0,  299.0,  132.0},
      {    128227.0,    137.0,   181.0,   -68982.0,   -9.0,   39.0},
      {    123457.0,     11.0,    19.0,   -53311.0,   32.0,   -4.0},
      {    156994.0,     10.0,  -168.0,    -1235.0,    0.0,   82.0},
      {     63110.0,     63.0,    27.0,   -33228.0,    0.0,   -9.0},
      {    -57976.0,    -63.0,  -189.0,    31429.0,    0.0,  -75.0},
      {    -59641.0,    -11.0,   149.0,    25543.0,  -11.0,   66.0},
      {    -51613.0,    -42.0,   129.0,    26366.0,    0.0,   78.0},
      {     45893.0,     50.0,    31.0,   -24236.0,  -10.0,   20.0},
      {     63384.0,     11.0,  -150.0,    -1220.0,    0.0,   29.0},
      {    -38571.0,     -1.0,   158.0,    16452.0,  -11.0,   68.0},
      {     32481.0,      0.0,     0.0,   -13870.0,    0.0,    0.0},
      {    -47722.0,      0.0,   -18.0,      477.0,    0.0,  -25.0},
      {    -31046.0,     -1.0,   131.0,    13238.0,  -11.0,   59.0},
      {     28593.0,      0.0,    -1.0,   -12338.0,   10.0,   -3.0},
      {     20441.0,     21.0,    10.0,   -10758.0,    0.0,   -3.0},
      {     29243.0,      0.0,   -74.0,     -609.0,    0.0,   13.0},
      {     25887.0,      0.0,   -66.0,     -550.0,    0.0,   11.0},
      {    -14053.0,    -25.0,    79.0,     8551.0,   -2.0,  -45.0},
      {     15164.0,     10.0,    11.0,    -8001.0,    0.0,   -1.0},
      {    -15794.0,     72.0,   -16.0,     6850.0,  -42.0,   -5.0},
      {     21783.0,      0.0,    13.0,     -167.0,    0.0,   13.0},
      {    -12873.0,    -10.0,   -37.0,     6953.0,    0.0,  -14.0},
      {    -12654.0,     11.0,    63.0,     6415.0,    0.0,   26.0},
      {    -10204.0,      0.0,    25.0,     5222.0,    0.0,   15.0},
      {     16707.0,    -85.0,   -10.0,      168.0,   -1.0,   10.0},
      {     -7691.0,      0.0,    44.0,     3268.0,    0.0,   19.0},
      {    -11024.0,      0.0,   -14.0,      104.0,    0.0,    2.0},
      {      7566.0,    -21.0,   -11.0,    -3250.0,    0.0,   -5.0},
      {     -6637.0,    -11.0,    25.0,     3353.0,    0.0,   14.0},
      {     -7141.0,     21.0,     8.0,     3070.0,    0.0,    4.0},
      {     -6302.0,    -11.0,     2.0,     3272.0,    0.0,    4.0},
      {      5800.0,     10.0,     2.0,    -3045.0,    0.0,   -1.0},
      {      6443.0,      0.0,    -7.0,    -2768.0,    0.0,   -4.0},
      {     -5774.0,    -11.0,   -15.0,     3041.0,    0.0,   -5.0},
      {     -5350.0,      0.0,    21.0,     2695.0,    0.0,   12.0},
      {     -4752.0,    -11.0,    -3.0,     2719.0,    0.0,   -3.0},
      {     -4940.0,    -11.0,   -21.0,     2720.0,    0.0,   -9.0},
      {      7350.0,      0.0,    -8.0,      -51.0,    0.0,    4.0},
      {      4065.0,      0.0,     6.0,    -2206.0,    0.0,    1.0},
      {      6579.0,      0.0,   -24.0,     -199.0,    0.0,    2.0},
      {      3579.0,      0.0,     5.0,    -1900.0,    0.0,    1.0},
      {      4725.0,      0.0,    -6.0,      -41.0,    0.0,    3.0},
      {     -3075.0,      0.0,    -2.0,     1313.0,    0.0,   -1.0},
      {     -2904.0,      0.0,    15.0,     1233.0,    0.0,    7.0},
      {      4348.0,      0.0,   -10.0,      -81.0,    0.0,    2.0},
      {     -2878.0,      0.0,     8.0,     1232.0,    0.0,    4.0},
      {     -4230.0,      0.0,     5.0,      -20.0,    0.0,   -2.0},
      {     -2819.0,      0.0,     7.0,     1207.0,    0.0,    3.0},
      {     -4056.0,      0.0,     5.0,       40.0,    0.0,   -2.0},
      {     -2647.0,      0.0,    11.0,     1129.0,    0.0,    5.0},
      {     -2294.0,      0.0,   -10.0,     1266.0,    0.0,   -4.0},
      {      2481.0,      0.0,    -7.0,    -1062.0,    0.0,   -3.0},
      {      2179.0,      0.0,    -2.0,    -1129.0,    0.0,   -2.0},
      {      3276.0,      0.0,     1.0,       -9.0,    0.0,    0.0},
      {     -3389.0,      0.0,     5.0,       35.0,    0.0,   -2.0},
      {      3339.0,      0.0,   -13.0,     -107.0,    0.0,    1.0},
      {     -1987.0,      0.0,    -6.0,     1073.0,    0.0,   -2.0},
      {     -1981.0,      0.0,     0.0,      854.0,    0.0,    0.0},
      {      4026.0,      0.0,  -353.0,     -553.0,    0.0, -139.0},
      {      1660.0,      0.0,    -5.0,     -710.0,    0.0,   -2.0},
      {     -1521.0,      0.0,     9.0,      647.0,    0.0,    4.0},
      {      1314.0,      0.0,     0.0,     -700.0,    0.0,    0.0},
      {     -1283.0,      0.0,     0.0,      672.0,    0.0,    0.0},
      {     -1331.0,      0.0,     8.0,      663.0,    0.0,    4.0},
      {      1383.0,      0.0,    -2.0,     -594.0,    0.0,   -2.0},
      {      1405.0,      0.0,     4.0,     -610.0,    0.0,    2.0},
      {      1290.0,      0.0,     0.0,     -556.0,    0.0,    0.0},
      {     -1214.0,      0.0,     5.0,      518.0,    0.0,    2.0},
      {      1146.0,      0.0,    -3.0,     -490.0,    0.0,   -1.0},
      {      1019.0,      0.0,    -1.0,     -527.0,    0.0,   -1.0},
      {     -1100.0,      0.0,     9.0,      465.0,    0.0,    4.0},
      {      -970.0,      0.0,     2.0,      496.0,    0.0,    1.0},
      {      1575.0,      0.0,    -6.0,      -50.0,    0.0,    0.0},
      {       934.0,      0.0,    -3.0,     -399.0,    0.0,   -1.0},
      {       922.0,      0.0,    -1.0,     -395.0,    0.0,   -1.0},
      {       815.0,      0.0,    -1.0,     -422.0,    0.0,   -1.0},
      {       834.0,      0.0,     2.0,     -440.0,    0.0,    1.0},
      {      1248.0,      0.0,     0.0,     -170.0,    0.0,    1.0},
      {      1338.0,      0.0,    -5.0,      -39.0,    0.0,    0.0},
      {       716.0,      0.0,    -2.0,     -389.0,    0.0,   -1.0},
      {      1282.0,      0.0,    -3.0,      -23.0,    0.0,    1.0},
      {       742.0,      0.0,     1.0,     -391.0,    0.0,    0.0},
      {      1020.0,      0.0,   -25.0,     -495.0,    0.0,  -10.0},
      {       715.0,      0.0,    -4.0,     -326.0,    0.0,    2.0},
      {      -666.0,      0.0,    -3.0,      369.0,    0.0,   -1.0},
      {      -667.0,      0.0,     1.0,      346.0,    0.0,    1.0},
      {      -704.0,      0.0,     0.0,      304.0,    0.0,    0.0},
      {      -694.0,      0.0,     5.0,      294.0,    0.0,    2.0},
      {     -1014.0,      0.0,    -1.0,        4.0,    0.0,   -1.0},
      {      -585.0,      0.0,    -2.0,      316.0,    0.0,   -1.0},
      {      -949.0,      0.0,     1.0,        8.0,    0.0,   -1.0},
      {      -595.0,      0.0,     0.0,      258.0,    0.0,    0.0},
      {       528.0,      0.0,     0.0,     -279.0,    0.0,    0.0},
      {      -590.0,      0.0,     4.0,      252.0,    0.0,    2.0},
      {       570.0,      0.0,    -2.0,     -244.0,    0.0,   -1.0},
      {      -502.0,      0.0,     3.0,      250.0,    0.0,    2.0},
      {      -875.0,      0.0,     1.0,       29.0,    0.0,    0.0},
      {      -492.0,      0.0,    -3.0,      275.0,    0.0,   -1.0},
      {       535.0,      0.0,    -2.0,     -228.0,    0.0,   -1.0},
      {      -467.0,      0.0,     1.0,      240.0,    0.0,    1.0},
      {       591.0,      0.0,     0.0,     -253.0,    0.0,    0.0},
      {      -453.0,      0.0,    -1.0,      244.0,    0.0,   -1.0},
      {       766.0,      0.0,     1.0,        9.0,    0.0,    0.0},
      {      -446.0,      0.0,     2.0,      225.0,    0.0,    1.0},
      {      -488.0,      0.0,     2.0,      207.0,    0.0,    1.0},
      {      -468.0,      0.0,     0.0,      201.0,    0.0,    0.0},
      {      -421.0,      0.0,     1.0,      216.0,    0.0,    1.0},
      {       463.0,      0.0,     0.0,     -200.0,    0.0,    0.0},
      {      -673.0,      0.0,     2.0,       14.0,    0.0,    0.0},
      {       658.0,      0.0,     0.0,       -2.0,    0.0,    0.0},
      {      -438.0,      0.0,     0.0,      188.0,    0.0,    0.0},
      {      -390.0,      0.0,     0.0,      205.0,    0.0,    0.0},
      {       639.0,    -11.0,    -2.0,      -19.0,    0.0,    0.0},
      {       412.0,      0.0,    -2.0,     -176.0,    0.0,   -1.0},
      {      -361.0,      0.0,     0.0,      189.0,    0.0,    0.0},
      {       360.0,      0.0,    -1.0,     -185.0,    0.0,   -1.0},
      {       588.0,      0.0,    -3.0,      -24.0,    0.0,    0.0},
      {      -578.0,      0.0,     1.0,        5.0,    0.0,    0.0},
      {      -396.0,      0.0,     0.0,      171.0,    0.0,    0.0},
      {       565.0,      0.0,    -1.0,       -6.0,    0.0,    0.0},
      {      -335.0,      0.0,    -1.0,      184.0,    0.0,   -1.0},
      {       357.0,      0.0,     1.0,     -154.0,    0.0,    0.0},
      {       321.0,      0.0,     1.0,     -174.0,    0.0,    0.0},
      {      -301.0,      0.0,    -1.0,      162.0,    0.0,    0.0},
      {      -334.0,      0.0,     0.0,      144.0,    0.0,    0.0},
      {       493.0,      0.0,    -2.0,      -15.0,    0.0,    0.0},
      {       494.0,      0.0,    -2.0,      -19.0,    0.0,    0.0},
      {       337.0,      0.0,    -1.0,     -143.0,    0.0,   -1.0},
      {       280.0,      0.0,    -1.0,     -144.0,    0.0,    0.0},
      {       309.0,      0.0,     1.0,     -134.0,    0.0,    0.0},
      {      -263.0,      0.0,     2.0,      131.0,    0.0,    1.0},
      {       253.0,      0.0,     1.0,     -138.0,    0.0,    0.0},
      {       245.0,      0.0,     0.0,     -128.0,    0.0,    0.0},
      {       416.0,      0.0,    -2.0,      -17.0,    0.0,    0.0},
      {      -229.0,      0.0,     0.0,      128.0,    0.0,    0.0},
      {       231.0,      0.0,     0.0,     -120.0,    0.0,    0.0},
      {      -259.0,      0.0,     2.0,      109.0,    0.0,    1.0},
      {       375.0,      0.0,    -1.0,       -8.0,    0.0,    0.0},
      {       252.0,      0.0,     0.0,     -108.0,    0.0,    0.0},
      {      -245.0,      0.0,     1.0,      104.0,    0.0,    0.0},
      {       243.0,      0.0,    -1.0,     -104.0,    0.0,    0.0},
      {       208.0,      0.0,     1.0,     -112.0,    0.0,    0.0},
      {       199.0,      0.0,     0.0,     -102.0,    0.0,    0.0},
      {      -208.0,      0.0,     1.0,      105.0,    0.0,    0.0},
      {       335.0,      0.0,    -2.0,      -14.0,    0.0,    0.0},
      {      -325.0,      0.0,     1.0,        7.0,    0.0,    0.0},
      {      -187.0,      0.0,     0.0,       96.0,    0.0,    0.0},
      {       197.0,      0.0,    -1.0,     -100.0,    0.0,    0.0},
      {      -192.0,      0.0,     2.0,       94.0,    0.0,    1.0},
      {      -188.0,      0.0,     0.0,       83.0,    0.0,    0.0},
      {       276.0,      0.0,     0.0,       -2.0,    0.0,    0.0},
      {      -286.0,      0.0,     1.0,        6.0,    0.0,    0.0},
      {       186.0,      0.0,    -1.0,      -79.0,    0.0,    0.0},
      {      -219.0,      0.0,     0.0,       43.0,    0.0,    0.0},
      {       276.0,      0.0,     0.0,        2.0,    0.0,    0.0},
      {      -153.0,      0.0,    -1.0,       84.0,    0.0,    0.0},
      {      -156.0,      0.0,     0.0,       81.0,    0.0,    0.0},
      {      -154.0,      0.0,     1.0,       78.0,    0.0,    0.0},
      {      -174.0,      0.0,     1.0,       75.0,    0.0,    0.0},
      {      -163.0,      0.0,     2.0,       69.0,    0.0,    1.0},
      {      -228.0,      0.0,     0.0,        1.0,    0.0,    0.0},
      {        91.0,      0.0,    -4.0,      -54.0,    0.0,   -2.0},
      {       175.0,      0.0,     0.0,      -75.0,    0.0,    0.0},
      {      -159.0,      0.0,     0.0,       69.0,    0.0,    0.0},
      {       141.0,      0.0,     0.0,      -72.0,    0.0,    0.0},
      {       147.0,      0.0,     0.0,      -75.0,    0.0,    0.0},
      {      -132.0,      0.0,     0.0,       69.0,    0.0,    0.0},
      {       159.0,      0.0,   -28.0,      -54.0,    0.0,   11.0},
      {       213.0,      0.0,     0.0,       -4.0,    0.0,    0.0},
      {       123.0,      0.0,     0.0,      -64.0,    0.0,    0.0},
      {      -118.0,      0.0,    -1.0,       66.0,    0.0,    0.0},
      {       144.0,      0.0,    -1.0,      -61.0,    0.0,    0.0},
      {      -121.0,      0.0,     1.0,       60.0,    0.0,    0.0},
      {      -134.0,      0.0,     1.0,       56.0,    0.0,    1.0},
      {      -105.0,      0.0,     0.0,       57.0,    0.0,    0.0},
      {      -102.0,      0.0,     0.0,       56.0,    0.0,    0.0},
      {       120.0,      0.0,     0.0,      -52.0,    0.0,    0.0},
      {       101.0,      0.0,     0.0,      -54.0,    0.0,    0.0},
      {      -113.0,      0.0,     0.0,       59.0,    0.0,    0.0},
      {      -106.0,      0.0,     0.0,       61.0,    0.0,    0.0},
      {      -129.0,      0.0,     1.0,       55.0,    0.0,    0.0},
      {      -114.0,      0.0,     0.0,       57.0,    0.0,    0.0},
      {       113.0,      0.0,    -1.0,      -49.0,    0.0,    0.0},
      {      -102.0,      0.0,     0.0,       44.0,    0.0,    0.0},
      {       -94.0,      0.0,     0.0,       51.0,    0.0,    0.0},
      {      -100.0,      0.0,    -1.0,       56.0,    0.0,    0.0},
      {        87.0,      0.0,     0.0,      -47.0,    0.0,    0.0},
      {       161.0,      0.0,     0.0,       -1.0,    0.0,    0.0},
      {        96.0,      0.0,     0.0,      -50.0,    0.0,    0.0},
      {       151.0,      0.0,    -1.0,       -5.0,    0.0,    0.0},
      {      -104.0,      0.0,     0.0,       44.0,    0.0,    0.0},
      {      -110.0,      0.0,     0.0,       48.0,    0.0,    0.0},
      {      -100.0,      0.0,     1.0,       50.0,    0.0,    0.0},
      {        92.0,      0.0,    -5.0,       12.0,    0.0,   -2.0},
      {        82.0,      0.0,     0.0,      -45.0,    0.0,    0.0},
      {        82.0,      0.0,     0.0,      -45.0,    0.0,    0.0},
      {       -78.0,      0.0,     0.0,       41.0,    0.0,    0.0},
      {       -77.0,      0.0,     0.0,       43.0,    0.0,    0.0},
      {         2.0,      0.0,     0.0,       54.0,    0.0,    0.0},
      {        94.0,      0.0,     0.0,      -40.0,    0.0,    0.0},
      {       -93.0,      0.0,     0.0,       40.0,    0.0,    0.0},
      {       -83.0,      0.0,    10.0,       40.0,    0.0,   -2.0},
      {        83.0,      0.0,     0.0,      -36.0,    0.0,    0.0},
      {       -91.0,      0.0,     0.0,       39.0,    0.0,    0.0},
      {       128.0,      0.0,     0.0,       -1.0,    0.0,    0.0},
      {       -79.0,      0.0,     0.0,       34.0,    0.0,    0.0},
      {       -83.0,      0.0,     0.0,       47.0,    0.0,    0.0},
      {        84.0,      0.0,     0.0,      -44.0,    0.0,    0.0},
      {        83.0,      0.0,     0.0,      -43.0,    0.0,    0.0},
      {        91.0,      0.0,     0.0,      -39.0,    0.0,    0.0},
      {       -77.0,      0.0,     0.0,       39.0,    0.0,    0.0},
      {        84.0,      0.0,     0.0,      -43.0,    0.0,    0.0},
      {       -92.0,      0.0,     1.0,       39.0,    0.0,    0.0},
      {       -92.0,      0.0,     1.0,       39.0,    0.0,    0.0},
      {       -94.0,      0.0,     0.0,        0.0,    0.0,    0.0},
      {        68.0,      0.0,     0.0,      -36.0,    0.0,    0.0},
      {       -61.0,      0.0,     0.0,       32.0,    0.0,    0.0},
      {        71.0,      0.0,     0.0,      -31.0,    0.0,    0.0},
      {        62.0,      0.0,     0.0,      -34.0,    0.0,    0.0},
      {       -63.0,      0.0,     0.0,       33.0,    0.0,    0.0},
      {       -73.0,      0.0,     0.0,       32.0,    0.0,    0.0},
      {       115.0,      0.0,     0.0,       -2.0,    0.0,    0.0},
      {      -103.0,      0.0,     0.0,        2.0,    0.0,    0.0},
      {        63.0,      0.0,     0.0,      -28.0,    0.0,    0.0},
      {        74.0,      0.0,     0.0,      -32.0,    0.0,    0.0},
      {      -103.0,      0.0,    -3.0,        3.0,    0.0,   -1.0},
      {       -69.0,      0.0,     0.0,       30.0,    0.0,    0.0},
      {        57.0,      0.0,     0.0,      -29.0,    0.0,    0.0},
      {        94.0,      0.0,     0.0,       -4.0,    0.0,    0.0},
      {        64.0,      0.0,     0.0,      -33.0,    0.0,    0.0},
      {       -63.0,      0.0,     0.0,       26.0,    0.0,    0.0},
      {       -38.0,      0.0,     0.0,       20.0,    0.0,    0.0},
      {       -43.0,      0.0,     0.0,       24.0,    0.0,    0.0},
      {       -45.0,      0.0,     0.0,       23.0,    0.0,    0.0},
      {        47.0,      0.0,     0.0,      -24.0,    0.0,    0.0},
      {       -48.0,      0.0,     0.0,       25.0,    0.0,    0.0},
      {        45.0,      0.0,     0.0,      -26.0,    0.0,    0.0},
      {        56.0,      0.0,     0.0,      -25.0,    0.0,    0.0},
      {        88.0,      0.0,     0.0,        2.0,    0.0,    0.0},
      {       -75.0,      0.0,     0.0,        0.0,    0.0,    0.0},
      {        85.0,      0.0,     0.0,        0.0,    0.0,    0.0},
      {        49.0,      0.0,     0.0,      -26.0,    0.0,    0.0},
      {       -74.0,      0.0,    -3.0,       -1.0,    0.0,   -1.0},
      {       -39.0,      0.0,     0.0,       21.0,    0.0,    0.0},
      {        45.0,      0.0,     0.0,      -20.0,    0.0,    0.0},
      {        51.0,      0.0,     0.0,      -22.0,    0.0,    0.0},
      {       -40.0,      0.0,     0.0,       21.0,    0.0,    0.0},
      {        41.0,      0.0,     0.0,      -21.0,    0.0,    0.0},
      {       -42.0,      0.0,     0.0,       24.0,    0.0,    0.0},
      {       -51.0,      0.0,     0.0,       22.0,    0.0,    0.0},
      {       -42.0,      0.0,     0.0,       22.0,    0.0,    0.0},
      {        39.0,      0.0,     0.0,      -21.0,    0.0,    0.0},
      {        46.0,      0.0,     0.0,      -18.0,    0.0,    0.0},
      {       -53.0,      0.0,     0.0,       22.0,    0.0,    0.0},
      {        82.0,      0.0,     0.0,       -4.0,    0.0,    0.0},
      {        81.0,      0.0,    -1.0,       -4.0,    0.0,    0.0},
      {        47.0,      0.0,     0.0,      -19.0,    0.0,    0.0},
      {        53.0,      0.0,     0.0,      -23.0,    0.0,    0.0},
      {       -45.0,      0.0,     0.0,       22.0,    0.0,    0.0},
      {       -44.0,      0.0,     0.0,       -2.0,    0.0,    0.0},
      {       -33.0,      0.0,     0.0,       16.0,    0.0,    0.0},
      {       -61.0,      0.0,     0.0,        1.0,    0.0,    0.0},
      {       -38.0,      0.0,     0.0,       19.0,    0.0,    0.0},
      {       -33.0,      0.0,     0.0,       21.0,    0.0,    0.0},
      {       -60.0,      0.0,     0.0,        0.0,    0.0,    0.0},
      {        48.0,      0.0,     0.0,      -10.0,    0.0,    0.0},
      {        38.0,      0.0,     0.0,      -20.0,    0.0,    0.0},
      {        31.0,      0.0,     0.0,      -13.0,    0.0,    0.0},
      {       -32.0,      0.0,     0.0,       15.0,    0.0,    0.0},
      {        45.0,      0.0,     0.0,       -8.0,    0.0,    0.0},
      {       -44.0,      0.0,     0.0,       19.0,    0.0,    0.0},
      {       -51.0,      0.0,     0.0,        0.0,    0.0,    0.0},
      {       -36.0,      0.0,     0.0,       20.0,    0.0,    0.0},
      {        44.0,      0.0,     0.0,      -19.0,    0.0,    0.0},
      {       -60.0,      0.0,     0.0,        2.0,    0.0,    0.0},
      {        35.0,      0.0,     0.0,      -18.0,    0.0,    0.0},
      {        47.0,      0.0,     0.0,       -1.0,    0.0,    0.0},
      {        36.0,      0.0,     0.0,      -15.0,    0.0,    0.0},
      {       -36.0,      0.0,     0.0,       20.0,    0.0,    0.0},
      {       -35.0,      0.0,     0.0,       19.0,    0.0,    0.0},
      {       -37.0,      0.0,     0.0,       19.0,    0.0,    0.0},
      {        32.0,      0.0,     0.0,      -16.0,    0.0,    0.0},
      {        35.0,      0.0,     0.0,      -14.0,    0.0,    0.0},
      {        32.0,      0.0,     0.0,      -13.0,    0.0,    0.0},
      {        65.0,      0.0,     0.0,       -2.0,    0.0,    0.0},
      {        47.0,      0.0,     0.0,       -1.0,    0.0,    0.0},
      {        32.0,      0.0,     0.0,      -16.0,    0.0,    0.0},
      {        37.0,      0.0,     0.0,      -16.0,    0.0,    0.0},
      {       -30.0,      0.0,     0.0,       15.0,    0.0,    0.0},
      {       -32.0,      0.0,     0.0,       16.0,    0.0,    0.0},
      {       -31.0,      0.0,     0.0,       13.0,    0.0,    0.0},
      {        37.0,      0.0,     0.0,      -16.0,    0.0,    0.0},
      {        31.0,      0.0,     0.0,      -13.0,    0.0,    0.0},
      {        49.0,      0.0,     0.0,       -2.0,    0.0,    0.0},
      {        32.0,      0.0,     0.0,      -13.0,    0.0,    0.0},
      {       -43.0,      0.0,     0.0,       18.0,    0.0,    0.0},
      {       -32.0,      0.0,     0.0,       14.0,    0.0,    0.0},
      {        30.0,      0.0,     0.0,        0.0,    0.0,    0.0},
      {       -34.0,      0.0,     0.0,       15.0,    0.0,    0.0},
      {       -36.0,      0.0,     0.0,        0.0,    0.0,    0.0},
      {       -38.0,      0.0,     0.0,        0.0,    0.0,    0.0},
      {       -31.0,      0.0,     0.0,        0.0,    0.0,    0.0},
      {       -34.0,      0.0,     0.0,        0.0,    0.0,    0.0},
      {       -35.0,      0.0,     0.0,        0.0,    0.0,    0.0},
      {        30.0,      0.0,     0.0,       -2.0,    0.0,    0.0},
      {         0.0,      0.0, -1988.0,        0.0,    0.0,-1679.0},
      {         0.0,      0.0,   -63.0,        0.0,    0.0,  -27.0},
      {         0.0,      0.0,   364.0,        0.0,    0.0,  176.0},
      {         0.0,      0.0, -1044.0,        0.0,    0.0, -891.0},
      {         0.0,      0.0,   330.0,        0.0,    0.0,    0.0},
      {         0.0,      0.0,    30.0,        0.0,    0.0,   14.0},
      {         0.0,      0.0,  -162.0,        0.0,    0.0, -138.0},
      {         0.0,      0.0,    75.0,        0.0,    0.0,    0.0}};

/*
   Planetary argument multipliers:
       L   L'  F   D   Om  Me  Ve  E  Ma  Ju  Sa  Ur  Ne  pre
*/
   static const short int napl_t[165][14] = {
      { 0,  0,  0,  0,  0,  0,  0,  8,-16,  4,  5,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -8, 16, -4, -5,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  8,-16,  4,  5,  0,  0,  2},
      { 0,  0,  1, -1,  1,  0,  0,  3, -8,  3,  0,  0,  0,  0},
      {-1,  0,  0,  0,  0,  0, 10, -3,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  4, -8,  3,  0,  0,  0,  0},
      { 0,  0,  1, -1,  1,  0,  0, -5,  8, -3,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  2, -5,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0,  0, -1,  0,  2, -5,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  2, -5,  0,  0,  0},
      { 0,  0,  1, -1,  1,  0,  0, -1,  0, -2,  5,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0, -2,  5,  0,  0,  1},
      { 1,  0,  0, -2,  0,  0, 19,-21,  3,  0,  0,  0,  0,  0},
      { 1,  0,  0, -1,  1,  0,  0, -1,  0,  2,  0,  0,  0,  0},
      {-2,  0,  0,  2,  1,  0,  0,  2,  0, -2,  0,  0,  0,  0},
      {-1,  0,  0,  0,  0,  0, 18,-16,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -8, 13,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -8, 13,  0,  0,  0,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0, -8, 12,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  8,-13,  0,  0,  0,  0,  0,  0},
      { 0,  0, -1,  1,  0,  0,  0,  0,  2,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  0, -1,  2,  0,  0,  0,  0,  0},
      {-1,  0,  0,  1,  0,  0,  3, -4,  0,  0,  0,  0,  0,  0},
      { 0,  0, -1,  1,  0,  0,  0,  1,  0,  0,  1,  0,  0,  0},
      { 0,  0, -2,  2,  0,  0,  5, -6,  0,  0,  0,  0,  0,  0},
      {-2,  0,  0,  2,  0,  0,  6, -8,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  8,-15,  0,  0,  0,  0,  0},
      { 2,  0,  0, -2,  1,  0,  0, -2,  0,  3,  0,  0,  0,  0},
      {-2,  0,  0,  2,  0,  0,  0,  2,  0, -3,  0,  0,  0,  0},
      {-1,  0,  0,  1,  0,  0,  0,  1,  0, -1,  0,  0,  0,  0},
      { 0,  0, -1,  1,  0,  0,  0,  1,  0,  1,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  0,  0,  0,  1,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  0, -1,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0,  0, -1,  0,  0, -1,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  0},
      { 0,  0,  1, -1,  1,  0,  0, -1,  0,  0,  1,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  1},
      { 0,  0,  0,  0,  1,  0,  8,-13,  0,  0,  0,  0,  0,  0},
      {-1,  0,  0,  0,  1,  0, 18,-16,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  0,  0,  0, -2,  5,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  0, -4,  8, -3,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  0,  4, -8,  3,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  0,  0,  0,  2, -5,  0,  0,  0},
      {-2,  0,  0,  2,  0,  0,  0,  2,  0, -2,  0,  0,  0,  0},
      { 1,  0,  0,  0,  1,  0,-18, 16,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0, -8, 13,  0,  0,  0,  0,  0,  0},
      { 0,  0,  1, -1,  1,  0,  0,  0, -2,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  1, -2,  0,  0,  0,  0,  0},
      { 0,  0,  1, -1,  1,  0,  0, -2,  2,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -1,  2,  0,  0,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0,  0, -1,  0,  0,  2,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  2},
      { 0,  0,  2, -2,  1,  0, -5,  6,  0,  0,  0,  0,  0,  0},
      { 0,  0, -1,  1,  0,  0,  5, -7,  0,  0,  0,  0,  0,  0},
      {-2,  0,  0,  2,  1,  0,  0,  2,  0, -3,  0,  0,  0,  0},
      { 0,  0,  1, -1,  1,  0,  0, -1,  0, -1,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0, -1,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0,  0, -1,  0,  1,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  0,  2},
      {-2,  0,  0,  2,  0,  0,  3, -3,  0,  0,  0,  0,  0,  0},
      { 2,  0,  0, -2,  1,  0,  0, -2,  0,  2,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  0,  1, -2,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  3, -5,  0,  0,  0,  0,  0,  0},
      { 0,  0,  1, -1,  1,  0, -3,  4,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -3,  5,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0, -3,  5,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -3,  5,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  2, -4,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0, -2,  4,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -5,  8,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -5,  8,  0,  0,  0,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0, -5,  7,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -5,  8,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  5, -8,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  1},
      { 0,  0,  1, -1,  1,  0,  0, -1,  0,  2,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  2},
      { 0,  0,  2, -2,  1,  0, -3,  3,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  3, -6,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  1,  0,  2, -3,  0,  0,  0,  0,  0,  0},
      { 0,  0,  2, -2,  1,  0,  0, -2,  0,  2,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -2,  3,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  2, -3,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  0,  3,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  3, -5,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  1, -2,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  2, -3,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -4,  7,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -4,  6,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -4,  6,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  4, -6,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -1,  1,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  1, -1,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  1, -1,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0, -1,  0,  4,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0, -1,  0,  3,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  1,  0, -3,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -2,  4,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0, -2,  4,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -6,  9,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  1,  0, -2,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  3, -4,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  3, -4,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  1,  0, -1,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  2, -2,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  1,  0,  0, -1,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  1,  0,  2, -5,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  1,  0,  1,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -5,  7,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -5,  7,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  1,  0,  2,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -2,  2,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  2, -2,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -1,  3,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0, -1,  3,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  2,  0, -3,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0, -2,  5,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -6,  8,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  2,  0, -2,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  4, -4,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -3,  3,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  3, -3,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  3, -3,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  2,  0, -1,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  2,  0, -1,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  3, -2,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -8, 15,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  6, -8,  3,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  0,  0,  1},
      { 0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0, -6, 16, -4, -5,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0, -2,  8, -3,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -8, 11,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  1,  2,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  2,  0,  1,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -3,  7,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  0,  4,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  2, -1,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -7,  9,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  4, -4,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  1,  1,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  3,  0, -2,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  5, -4,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  3, -2,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  3,  0, -1,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  4, -2,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -8, 10,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  5, -5,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0, -9, 11,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  4,  0, -3,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  6, -6,  0,  0,  0,  0,  0,  0},
      { 0,  0,  0,  0,  0,  0,  0,  4,  0, -2,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  3, -1,  0,  0,  0,  0,  0,  2},
      { 0,  0,  0,  0,  0,  0,  0,  4,  0, -1,  0,  0,  0,  2},
      {-1,  0,  0,  2,  0,  0,  0,  2,  0, -2,  0,  0,  0,  0},
      { 1,  0,  2,  0,  2,  0,  0,  1,  0,  0,  0,  0,  0,  0},
      {-1,  0,  2,  0,  2,  0,  0, -4,  8, -3,  0,  0,  0,  0}};

/*
   Planetary nutation coefficients, unit 1e-7 arcsec:
   longitude (sin, cos), obliquity (sin, cos)

   Each row of coefficients in 'cpl_t' belongs with the corresponding
   row of fundamental-argument multipliers in 'napl_t'.
*/

   static const double cpl_t[165][4] = {
      { 1440.0,       0.0,       0.0,       0.0},
      {   56.0,    -117.0,     -42.0,     -40.0},
      {  125.0,     -43.0,       0.0,     -54.0},
      { -114.0,       0.0,       0.0,      61.0},
      { -219.0,      89.0,       0.0,       0.0},
      { -462.0,    1604.0,       0.0,       0.0},
      {   99.0,       0.0,       0.0,     -53.0},
      {   14.0,    -218.0,     117.0,       8.0},
      {   31.0,    -481.0,    -257.0,     -17.0},
      { -491.0,     128.0,       0.0,       0.0},
      {-3084.0,    5123.0,    2735.0,    1647.0},
      {-1444.0,    2409.0,   -1286.0,    -771.0},
      {  103.0,     -60.0,       0.0,       0.0},
      {  -26.0,     -29.0,     -16.0,      14.0},
      {  284.0,       0.0,       0.0,    -151.0},
      {  226.0,     101.0,       0.0,       0.0},
      {  -41.0,     175.0,      76.0,      17.0},
      {  425.0,     212.0,    -133.0,     269.0},
      { 1200.0,     598.0,     319.0,    -641.0},
      {  235.0,     334.0,       0.0,       0.0},
      {  266.0,     -78.0,       0.0,       0.0},
      { -460.0,    -435.0,    -232.0,     246.0},
      {    0.0,     131.0,       0.0,       0.0},
      {  -42.0,      20.0,       0.0,       0.0},
      {  -10.0,     233.0,       0.0,       0.0},
      {   78.0,     -18.0,       0.0,       0.0},
      {   45.0,     -22.0,       0.0,       0.0},
      {   89.0,     -16.0,      -9.0,     -48.0},
      { -349.0,     -62.0,       0.0,       0.0},
      {  -53.0,       0.0,       0.0,       0.0},
      {  -21.0,     -78.0,       0.0,       0.0},
      {   20.0,     -70.0,     -37.0,     -11.0},
      {   32.0,      15.0,      -8.0,      17.0},
      {  174.0,      84.0,      45.0,     -93.0},
      {   11.0,      56.0,       0.0,       0.0},
      {  -66.0,     -12.0,      -6.0,      35.0},
      {   47.0,       8.0,       4.0,     -25.0},
      {   46.0,      66.0,      35.0,     -25.0},
      {  -68.0,     -34.0,     -18.0,      36.0},
      {   76.0,      17.0,       9.0,     -41.0},
      {   84.0,     298.0,     159.0,     -45.0},
      {  -82.0,     292.0,     156.0,      44.0},
      {  -73.0,      17.0,       9.0,      39.0},
      { -439.0,       0.0,       0.0,       0.0},
      {   57.0,     -28.0,     -15.0,     -30.0},
      {  -40.0,      57.0,      30.0,      21.0},
      {  273.0,      80.0,      43.0,    -146.0},
      { -449.0,     430.0,       0.0,       0.0},
      {   -8.0,     -47.0,     -25.0,       4.0},
      {    6.0,      47.0,      25.0,      -3.0},
      {  -48.0,    -110.0,     -59.0,      26.0},
      {   51.0,     114.0,      61.0,     -27.0},
      { -133.0,       0.0,       0.0,      57.0},
      {  -18.0,    -436.0,    -233.0,       9.0},
      {   35.0,      -7.0,       0.0,       0.0},
      {  -53.0,      -9.0,      -5.0,      28.0},
      {  -50.0,     194.0,     103.0,      27.0},
      {  -13.0,      52.0,      28.0,       7.0},
      {  -91.0,     248.0,       0.0,       0.0},
      {    6.0,      49.0,      26.0,      -3.0},
      {   -6.0,     -47.0,     -25.0,       3.0},
      {   52.0,      23.0,      10.0,     -23.0},
      { -138.0,       0.0,       0.0,       0.0},
      {   54.0,       0.0,       0.0,     -29.0},
      {  -37.0,      35.0,      19.0,      20.0},
      { -145.0,      47.0,       0.0,       0.0},
      {  -10.0,      40.0,      21.0,       5.0},
      {   11.0,     -49.0,     -26.0,      -7.0},
      {-2150.0,       0.0,       0.0,     932.0},
      {   85.0,       0.0,       0.0,     -37.0},
      {  -86.0,     153.0,       0.0,       0.0},
      {  -51.0,       0.0,       0.0,      22.0},
      {  -11.0,    -268.0,    -116.0,       5.0},
      {   31.0,       6.0,       3.0,     -17.0},
      {  140.0,      27.0,      14.0,     -75.0},
      {   57.0,      11.0,       6.0,     -30.0},
      {  -14.0,     -39.0,       0.0,       0.0},
      {  -25.0,      22.0,       0.0,       0.0},
      {   42.0,     223.0,     119.0,     -22.0},
      {  -27.0,    -143.0,     -77.0,      14.0},
      {    9.0,      49.0,      26.0,      -5.0},
      {-1166.0,       0.0,       0.0,     505.0},
      {  117.0,       0.0,       0.0,     -63.0},
      {    0.0,      31.0,       0.0,       0.0},
      {    0.0,     -32.0,     -17.0,       0.0},
      {   50.0,       0.0,       0.0,     -27.0},
      {   30.0,      -3.0,      -2.0,     -16.0},
      {    8.0,     614.0,       0.0,       0.0},
      { -127.0,      21.0,       9.0,      55.0},
      {  -20.0,      34.0,       0.0,       0.0},
      {   22.0,     -87.0,       0.0,       0.0},
      {  -68.0,      39.0,       0.0,       0.0},
      {    3.0,      66.0,      29.0,      -1.0},
      {  490.0,       0.0,       0.0,    -213.0},
      {  -22.0,      93.0,      49.0,      12.0},
      {  -46.0,      14.0,       0.0,       0.0},
      {   25.0,     106.0,      57.0,     -13.0},
      { 1485.0,       0.0,       0.0,       0.0},
      {   -7.0,     -32.0,     -17.0,       4.0},
      {   30.0,      -6.0,      -2.0,     -13.0},
      {  118.0,       0.0,       0.0,     -52.0},
      {  -28.0,      36.0,       0.0,       0.0},
      {   14.0,     -59.0,     -31.0,      -8.0},
      { -458.0,       0.0,       0.0,     198.0},
      {    0.0,     -45.0,     -20.0,       0.0},
      { -166.0,     269.0,       0.0,       0.0},
      {  -78.0,      45.0,       0.0,       0.0},
      {   -5.0,     328.0,       0.0,       0.0},
      {-1223.0,     -26.0,       0.0,       0.0},
      { -368.0,       0.0,       0.0,       0.0},
      {  -75.0,       0.0,       0.0,       0.0},
      {  -13.0,     -30.0,       0.0,       0.0},
      {  -74.0,       0.0,       0.0,      32.0},
      { -262.0,       0.0,       0.0,     114.0},
      {  202.0,       0.0,       0.0,     -87.0},
      {   -8.0,      35.0,      19.0,       5.0},
      {  -35.0,     -48.0,     -21.0,      15.0},
      {   12.0,      55.0,      29.0,      -6.0},
      { -598.0,       0.0,       0.0,       0.0},
      {    8.0,     -31.0,     -16.0,      -4.0},
      {  113.0,       0.0,       0.0,     -49.0},
      {   83.0,      15.0,       0.0,       0.0},
      {    0.0,    -114.0,     -49.0,       0.0},
      {  117.0,       0.0,       0.0,     -51.0},
      {  393.0,       3.0,       0.0,       0.0},
      {   18.0,     -29.0,     -13.0,      -8.0},
      {    8.0,      34.0,      18.0,      -4.0},
      {   89.0,       0.0,       0.0,       0.0},
      {   54.0,     -15.0,      -7.0,     -24.0},
      {    0.0,      35.0,       0.0,       0.0},
      { -154.0,     -30.0,     -13.0,      67.0},
      {   80.0,     -71.0,     -31.0,     -35.0},
      {   61.0,     -96.0,     -42.0,     -27.0},
      {  123.0,    -415.0,    -180.0,     -53.0},
      {    0.0,       0.0,       0.0,     -35.0},
      {    7.0,     -32.0,     -17.0,      -4.0},
      {  -89.0,       0.0,       0.0,      38.0},
      {    0.0,     -86.0,     -19.0,      -6.0},
      { -123.0,    -416.0,    -180.0,      53.0},
      {  -62.0,     -97.0,     -42.0,      27.0},
      {  -85.0,     -70.0,     -31.0,      37.0},
      {  163.0,     -12.0,      -5.0,     -72.0},
      {  -63.0,     -16.0,      -7.0,      28.0},
      {  -21.0,     -32.0,     -14.0,       9.0},
      {    5.0,    -173.0,     -75.0,      -2.0},
      {   74.0,       0.0,       0.0,     -32.0},
      {   83.0,       0.0,       0.0,       0.0},
      { -339.0,       0.0,       0.0,     147.0},
      {   67.0,     -91.0,     -39.0,     -29.0},
      {   30.0,     -18.0,      -8.0,     -13.0},
      {    0.0,    -114.0,     -50.0,       0.0},
      {  517.0,      16.0,       7.0,    -224.0},
      {  143.0,      -3.0,      -1.0,     -62.0},
      {   50.0,       0.0,       0.0,     -22.0},
      {   59.0,       0.0,       0.0,       0.0},
      {  370.0,      -8.0,       0.0,    -160.0},
      {   34.0,       0.0,       0.0,     -15.0},
      {  -37.0,      -7.0,      -3.0,      16.0},
      {   40.0,       0.0,       0.0,       0.0},
      { -184.0,      -3.0,      -1.0,      80.0},
      {   31.0,      -6.0,       0.0,     -13.0},
      {   -3.0,     -32.0,     -14.0,       1.0},
      {  -34.0,       0.0,       0.0,       0.0},
      {  126.0,     -63.0,     -27.0,     -55.0},
      { -126.0,     -63.0,     -27.0,      55.0}};

/*
   Interval between fundamental epoch J2000.0 and given date.
*/

   t = ((jd_high - T0) + jd_low) / 36525.0;

/*
   Compute fundamental arguments from Simon et al. (1994),
   in radians.
*/

   fund_args (t, a);

/*
   ** Luni-solar nutation. **
*/

/*
   Initialize the nutation values.
*/

   dp = 0.0;
   de = 0.0;

/*
   Summation of luni-solar nutation series (in reverse order).
*/

   for (i = 322; i >= 0; i--)
   {

/*
   Argument and functions.
*/

      arg = fmod ((double) nals_t[i][0] * a[0]  +
                  (double) nals_t[i][1] * a[1]  +
                  (double) nals_t[i][2] * a[2]  +
                  (double) nals_t[i][3] * a[3]  +
                  (double) nals_t[i][4] * a[4], TWOPI);

      sarg = sin (arg);
      carg = cos (arg);

/*
   Term.
*/

      dp += (cls_t[i][0] + cls_t[i][1] * t) * sarg
              +   cls_t[i][2] * carg;
      de += (cls_t[i][3] + cls_t[i][4] * t) * carg
              +   cls_t[i][5] * sarg;
   }

/*
   Convert from 0.1 microarcsec units to radians.
*/

   factor = 1.0e-7 * ASEC2RAD;
   dpsils = dp * factor;
   depsls = de * factor;

/*
   ** Planetary nutation. **
*/

/*
   Planetary longitudes, Mercury through Neptune, wrt mean dynamical
   ecliptic and equinox of J2000, with high order terms omitted
   (Simon et al. 1994, 5.8.1-5.8.8).
*/

   alme = fmod (4.402608842461 + 2608.790314157421 * t, TWOPI);
   alve = fmod (3.176146696956 + 1021.328554621099 * t, TWOPI);
   alea = fmod (1.753470459496 +  628.307584999142 * t, TWOPI);
   alma = fmod (6.203476112911 +  334.061242669982 * t, TWOPI);
   alju = fmod (0.599547105074 +   52.969096264064 * t, TWOPI);
   alsa = fmod (0.874016284019 +   21.329910496032 * t, TWOPI);
   alur = fmod (5.481293871537 +    7.478159856729 * t, TWOPI);
   alne = fmod (5.311886286677 +    3.813303563778 * t, TWOPI);

/*
   General precession in longitude (Simon et al. 1994), equivalent
   to 5028.8200 arcsec/cy at J2000.
*/

   apa = (0.024380407358 + 0.000005391235 * t) * t;

/*
   Initialize the nutation values.
*/

   dp = 0.0;
   de = 0.0;

/*
   Summation of planetary nutation series (in reverse order).
*/

   for (i = 164; i >= 0; i--)
   {

/*
   Argument and functions.
*/

      arg = fmod ((double) napl_t[i][ 0] * a[0]  +
                  (double) napl_t[i][ 1] * a[1]  +
                  (double) napl_t[i][ 2] * a[2]  +
                  (double) napl_t[i][ 3] * a[3]  +
                  (double) napl_t[i][ 4] * a[4]  +
                  (double) napl_t[i][ 5] * alme  +
                  (double) napl_t[i][ 6] * alve  +
                  (double) napl_t[i][ 7] * alea  +
                  (double) napl_t[i][ 8] * alma  +
                  (double) napl_t[i][ 9] * alju  +
                  (double) napl_t[i][10] * alsa  +
                  (double) napl_t[i][11] * alur  +
                  (double) napl_t[i][12] * alne  +
                  (double) napl_t[i][13] * apa, TWOPI);

      sarg = sin (arg);
      carg = cos (arg);

/*
   Term.
*/

      dp += cpl_t[i][0] * sarg + cpl_t[i][1] * carg;
      de += cpl_t[i][2] * sarg + cpl_t[i][3] * carg;
   }

   dpsipl = dp * factor;
   depspl = de * factor;

/*
   Total: Add planetary and luni-solar components.
*/

   *dpsi = dpsipl + dpsils;
   *deps = depspl + depsls;

   return;
}

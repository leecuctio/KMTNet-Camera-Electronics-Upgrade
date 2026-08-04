/*!
  \file xtv.c
  \brief XVista TV Display Functions

  High-level functions that call the myzimage functions for image
  display.  Most applications will call these functions rather
  than the low-level myzimage routines.

*/

#include "xtv.h"  // XTV display header

extern int TVisOpen;
extern int yup;
extern int ncolors;

/*!
  \brief Open the XTV display

  \param nx Width of the image display window in screen pixels
  \param ny Height of the image display window in screen pixels 
  \param nclrs number of colors to use
  \param zoomf zoom factor for the zoom window (0=no zoom window)
  \param parity 1=flip Y-axis, 0=native order
  \param resource string with the resource variable (e.g., xtv.geometry)
  \param title title to appear on the window top banner

  \return file descriptor of X events on success

  Opens the XTV image display with the requested properties

*/

int
xtvopen(int nx, int ny, int nclrs, int zoomf,
	int parity, char *resource, char *title)
{
  int ierr;
  int i;
  int xoff,yoff;

  // Some defaults

  xoff = 20;
  yoff = 20;

  ierr = imageinit(&nx,&ny,&nclrs,zoomf,parity,resource,title,xoff,yoff); 
  if (ierr < 0) return(ierr); 

  ncolors = nclrs;
  return ierr;

}

/*!
  \brief Close the XTV display

  Convenience function for xtvopen().  Might perform other functions
  someday, so not totally trivial.
*/

void
xtvclose()
{
  imageclose();
}

/*!
  \brief load an image onto the image display

  \param a Input floating image array                   
  \param nx Number of X-axis pixels to be displayed
  \param ny Number of Y-axis pixels to be displayed
  \param nxfull Number of X-axis pixels in the full frame
  \param isx Address of the first X-axis pixel to be displayed (usually 0 = first pixel) 
  \param isy Address of the first Y-axis pixel to be displayed (usually 0 = first pixel) 
  \param psx X-axis image-space coordinate corresponding to isx (typically, if isx=0, psx=1)
  \param psy Y-axis image-space coordinate corresponding to isy (typically, if isy=0, psy=1) 
  \param z1 Intensity mapping lower limit
  \param z2 Intensity mapping upper limit                
  \param flip Flag for up/down image reflection (1=Y increases up, 0=Y increases down or native screen memory order)
  \param erase Flag to erase screen before display                  
  \param color Color plane to load (1=R,2=G,3=B,0=all)

  Loads an image into the image display, mapping data
  values into colors.

*/

int
xtvload(float *a, int nx, int ny, int nxfull, int isx, int isy, int psx,
       int psy, float z1, float z2, int flip, int erase, int color)
{
  float zero, span;

  zero = z1;
  span = z2-z1;

  if (flip == 1)
    yup = 1;
  else
    yup = 0;

  imagemap(zero,span,ncolors);
  imagevnull();
  if (erase) 
    imageerase();
  lights(4);
  imagedisplay(isx,isy,nx,ny,nxfull,psx,psy,a,color);
  lights(-1);
  lights(2);
  lights(3);
  
  return 0;
}

/*!
  \brief Load RGB color lookup tables

  \param r pointer to the red vector
  \param g pointer to the green vector
  \param b pointer to the blue vector
  \param n number of entries in each RGB table

  \sa bwcmap(), ibwcmap()
*/

void
xtvcolorld(short *r, short *g, short *b, int n)
{
  short ro[4], go[4], bo[4]; // Overlay plane colors (4 reserved)

  //  Set the colors reserved for the overlay plane

  ro[0] = *(r+n-1);  // overlay color 1 = last color in LUT
  go[0] = *(g+n-1);
  bo[0] = *(b+n-1);

  ro[1] = 255;  // overlay color 1 = Red
  go[1] = 0;
  bo[1] = 0;

  ro[2] = 0;    // overlay color 2 = Green
  go[2] = 255;
  bo[2] = 0;

  ro[3] = 0;    // overlay color 3 = Blue
  go[3] = 0;
  bo[3] = 255;

  imagepalette(4,ro,go,bo,1);

  // Temporarily fill in the overlay color, set the color map, then
  // return to original color map

  *(r+n-1) = *(r+n-2);
  *(g+n-1) = *(g+n-2);
  *(b+n-1) = *(b+n-2);

  imagepalette(n,r,g,b,0);

  *(r+n-1) = ro[0];
  *(g+n-1) = go[0];
  *(b+n-1) = bo[0];

}

/*!
  \brief loads a simple black-and-white color map

  \param r pointer to the red vector
  \param g pointer to the green vector
  \param b pointer to the blue vector

  \sa xtvcolorld(), ibwcamp()
*/

void
bwcmap(short *r, short *g, short *b)
{
  int i;

  for (i=0; i<256; i++) {
    r[i] = i;
    g[i] = i;
    b[i] = i;
  }
}

/*!
  \brief loads a simple inverse black-and-white color map

  \param r pointer to the red vector
  \param g pointer to the green vector
  \param b pointer to the blue vector

  \sa xtvcolorld(), bwcmap()
*/

void
ibwcmap(short *r, short *g, short *b)
{
  int i;

  for (i=0; i<256; i++) {
    r[i] = 255-i;
    g[i] = 255-i;
    b[i] = 255-i;
  }
}

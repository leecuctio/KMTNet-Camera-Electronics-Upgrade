#ifndef XTV_H
#define XTV_H

/*!
  \file xtv.h
  \brief Header file of global static variables for zimage.c

  DEFINITION OF X-WINDOWS WINDOW AND IMAGE

  <ol>

  <li>The base window "wbase" exists with size (width,height+XYZHEIGHT).
  In the portion not covered by subwindows the image is displayed.

  <li>In the upper left is the image window "wimage" with size
  (width,height).  This is where the images are displayed.

  <li>At the lower left is the palette subwindow "wpal" with size
  (palwidth,palheight).  It displays the palette, and allows interactive
  palette control by dragging the mouse.

  <li> At the lower middle are two light subwindows "wlgt1" (upper) and
  "wlgt2" with size (lgtwidth,lgtheigt).  They display status
  information with text and color.

  <li>At the lower right is the xyz display subwindow "wxyz" with size
  (xyzwidth,xyzheight).  This displays the (x,y) coordinates of the
  mouse as well as the data value at that position and any marker key
  that has been struck.

  <li>The zoom window is an independent window with size
  (zwidth,zheight).  It shows a zoomed version of the location of the
  mouse.
</ol>
<pre>
       +-------------------------+      +-------+
       |                         |      |       |
       |                         |      | Zoom  |
       |                         |      |       |
       |                         |      +-------+
       |        Image            |
       |                         |
       |                         |
       |                         |
       |                         |
       |                         |
       +-------------------------+
       | Palette | L1 | x y z    |
       |         | L2 |          |
       +-------------------------+
</pre>
 
   All subwindows have the same size XYZHEIGHT with a border size of 
   XYZBORDER (so their size is actually XYZHEIGHT - 2*XYZBORDER), and are 
   placed along the bottom of the window according to the following scheme:
   <ol>
   <li>XYZBORDER exists between all windows.
   <li>xzywidth gets 20*fontwidth for (%4d %4d %6d %1d) display of x y z k
   <li>lgtwidth gets (MAXMESS+1)*fontwidth for (%MAXMESSs) display of message
   <li>palwidth gets the rest.
   </ol>

   There are a number of coordinate systems used here:
   <ol>
   <li>USER COORDS: (coordinate system that is gone but not forgotten)

   <li>DATA COORDS: Data array passed to the image routines by the user
   Pixel (0,0) is (offx,offy) in USER COORDS dimensions of the data
   array are (datw,dath)

   <li>IMAGE COORDS: This the portion of the data which is displayed
   Pixel (0,0) is (datx,daty) in DATA coords dimensions of the image
   array are (imw,imh)

   <li>WINDOW COORDS: This is the display screen window dimensions are
   (width,height) location of UL of image in window is (winx,winy)
   location of UL displayed pixel in IMAGE is (imx,imy)
   </ol>

   The IMAGE may be zoomed by a factor of zim.

   y may increase downwards (yup==0) or upwards (yup==1)

   The transformations between different coordinate systems are
   <pre>
   Xi = (Xw - winx) / zim + imx         
   Yi = (Yw - winy) / zim + imy

   Xd = Xi + datx                       
   Yd = Yi + daty                 (yup==0)
      = imh-1 - Yi +daty          (yup==1)

   Xu = Xd + offx 
   Yu = Yd + offy
   </pre>

   The data is passed to the imaging routines as floating point with the
   address of the start of the array saved as "data", and is immediately
   converted to (byte) color addresses and saved as "image". The size of
   this image is (imw,imh), and the size of the (zoomed) image in the
   window is (winw,winh). Displayed in the window is a copy of this
   array that has been expanded by a factor of "zim", or squashed by a
   factor of "-zim". The image may under or overfill the window, and the
   mapping between image coordinates and window coordinates is provided
   by (imx,imy), which are the image coordinates of the upper left hand
   displayed pixel, and (winx,winy) which are the window coordinates of
   the upper left hand displayed pixel. Note that all coordinates run
   from left to right and top to bottom, and that an expanded display
   has the upper left corner of a pixel on an even multiple of window
   pixels.
<pre>
    +------------------------------------------------------------------------+
    |        |                                                               |
    |      offy              Original Data                                   |
    |        |                                                               |
    |        +-----------------------------------------------------+ .       |
    |<-offx->|        |                                            | .       |
    |        |      daty           Data Array                      | .       |
    |        |        |                                            | .       |
    |        |        +---------------------------------------+ .  | .       |
    |        |<-datx->|       |                               | .  | .       |
    |        |        |      imy        Image (if bigger      | .  | .       |
    |        |        |       |                than display)  | .  | .       |
    |        |        |       +--------------------------+ .  | .  | .       |
    |        |        |<-imx->|//////|///////////////////| .  | .  | .       |
    |        |        |       |////(winy)// Display /////| .  | .  | .       |
    |        |        |       |//////|///////////////////| .  | .  | .       |
    |        |        |       |(winx)+----------+////////| .  | .  | .       |
    |        |        |       |//////|Image (if |////////| .  |imh | .       |
    |        |        |       |//////| smaller  |////////|winh| .  |dath     |
    |        |        |       |//////|  than    |////////| .  | .  | .       |
    |        |        |       |//////| display) |////////| .  | .  | .       |
    |        |        |       |//////+----------+////////| .  | .  | .       |
    |        |        |       |//////////////////////////| .  | .  | .       |
    |        |        |       +--------------------------+ .  | .  | .       |
    |        |        |       ........... winw ...........    | .  | .       |
    |        |        +---------------------------------------+ .  | .       |
    |        |        .................. imw ..................    | .       |
    |        |                                                     | .       |
    |        +-----------------------------------------------------+ .       |
    |        ........................ datw .........................         |
    +________________________________________________________________________+
</pre>

*/

// System Header Files we need

#include <stdio.h>
#include <signal.h>
#include <string.h>
#include <stdlib.h>
#include <signal.h>
#include <unistd.h>

// X11 headers

#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/Xresource.h>
#include <X11/cursorfont.h>
#include <X11/keysym.h>

#define __HAIRS

// global definitions


#define XYZHEIGHT 60
#define XYZWIDTH 35
#define XYZBORDER 1
#define DEFZOOMSIZE 32
#define DEFZOOMSIZE 32

#define PICTDEFAULT   "+10+10"
#define DEFAULT_FONT1 "6x10" 
#define DEFAULT_FONT2 "fixed" 
#define DEFZOOMFAC 4       //!< default zoom factor
#define MAXCOLORS 121      //!< maximum number of colors
#define MAXPALWIDTH 1024   //!< maximum palette size
#define MAXVEC 400000	   //!< maximum number of vectors saved 
#define MAXTEXT 100	   //!< maximum number of text saved 
#define MAXZCURS 64	   //!< maximum number of zoom cursor vectors 
#define MAXMESS 7	   //!< maximum number of chars in message 
#define MAXSCREENPIX 1<<21 //!< maximum number of screen pixels
#define MAXZOOMFACTOR 32   //!< maximum zoom factor

#define DEFMAXWIDTH  1600  //!< default maximum image width in pixels
#define DEFMAXHEIGHT 1024  //!< default maximum image height in pixels

#define MAXSTRINGWID   32  //!< maximum length of a coordinate display string
#define NXYZ 32            //!< maximum length of an xyz string
#define KEYLEN 10

// Some Macros...

#define MIN(a,b) (((a) < (b)) ? (a) : (b))
#define MAX(a,b) (((a) > (b)) ? (a) : (b))
#define ABS(a) (((a) > 0) ? (a) : -(a))

#define USERXCOORD(x) ( (zim > 0) ? \
       (((x)-winx)/zim+imx+datx+offx) : ((-zim)*((x)-winx)+imx+datx+offx) )

#define USERYCOORD(y) ( ( (zim > 0) ? \
  ( (yup==0) ? (((y)-winy)/zim+imy)    : (imh-1-((y)-winy)/zim-imy) ) \
                         : \
  ( (yup==0) ? ((-zim)*((y)-winy)+imy) : (imh-1-(-zim)*((y)-winy)-imy) ) \
                         ) + daty+offy )

#define MAXSTORE 4  //!< maximum number of images to stor in the ring buffer


// Bit map of image cursor 

#define curs_width 16
#define curs_height 16
#define curs_x_hot 7
#define curs_y_hot 7

#ifndef OPENCURS

// Regular cursor 

static char curs_bits[] = {
   0x80, 0x00, 0x80, 0x00, 0x80, 0x00, 0x80, 0x00, 0x80, 0x00, 0x80, 0x00,
   0x40, 0x01, 0x3f, 0x7e, 0x40, 0x01, 0x80, 0x00, 0x80, 0x00, 0x80, 0x00,
   0x80, 0x00, 0x80, 0x00, 0x80, 0x00, 0x00, 0x00
};

static char curs_mask_bits[] = {
   0xc0, 0x01, 0xc0, 0x01, 0xc0, 0x01, 0xc0, 0x01, 0xc0, 0x01, 0xc0, 0x01,
   0x7f, 0x7f, 0x3f, 0x7e, 0x7f, 0x7f, 0xc0, 0x01, 0xc0, 0x01, 0xc0, 0x01,
   0xc0, 0x01, 0xc0, 0x01, 0xc0, 0x01, 0x00, 0x00
};

#else
// Cursor with bigger central open hole 

static char curs_bits[] = {
   0x80, 0x00, 0x80, 0x00, 0x80, 0x00, 0x80, 0x00, 0x80, 0x00, 0x00, 0x00,
   0x00, 0x00, 0x1f, 0x7c, 0x00, 0x00, 0x00, 0x00, 0x80, 0x00, 0x80, 0x00,
   0x80, 0x00, 0x80, 0x00, 0x80, 0x00, 0x00, 0x00
};

static char curs_mask_bits[] = {
   0xc0, 0x01, 0xc0, 0x01, 0xc0, 0x01, 0xc0, 0x01, 0xc0, 0x01, 0x40, 0x01,
   0x3f, 0x7e, 0x1f, 0x7c, 0x3f, 0x7e, 0x40, 0x01, 0xc0, 0x01, 0xc0, 0x01,
   0xc0, 0x01, 0xc0, 0x01, 0xc0, 0x01, 0x00, 0x00
};

#endif

// Bit map of palette cursor 

#define palcurs_width 16
#define palcurs_height 16
#define palcurs_x_hot 8
#define palcurs_y_hot 7

static char palcurs_bits[] = {
   0x00, 0x01, 0x00, 0x01, 0x00, 0x01, 0x00, 0x01, 0x00, 0x01, 0x00, 0x01,
   0x00, 0x01, 0x00, 0x01, 0x00, 0x01, 0x00, 0x01, 0x00, 0x01, 0x00, 0x01,
   0x00, 0x01, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00
};

static char palcurs_mask_bits[] = {
   0x80, 0x03, 0x80, 0x03, 0x80, 0x03, 0x80, 0x03, 0x80, 0x03, 0x80, 0x03,
   0x80, 0x03, 0x80, 0x03, 0x80, 0x03, 0x80, 0x03, 0x80, 0x03, 0x80, 0x03,
   0x80, 0x03, 0x80, 0x03, 0x80, 0x03, 0x00, 0x00
};

// Error Codes

#define ERR_CANT_OPEN_DISPLAY	     -1 //!< Cannot open the image display window
#define ERR_CANT_CREATE_IMAGE_WINDOW -2 //!< Cannot create the image window
#define ERR_CANT_CREATE_ZOOM_WINDOW  -3 //!< Cannot create the zoom window
#define ERR_INSUFF_VECTOR_COLORS     -4 //!< Insufficient colors
#define ERR_INSUFF_STATUS_COLORS     -5 //!< Insufficient status light colors
#define ERR_INSUFF_IMAGE_COLORS	     -6 //!< Insufficient colors for image window
#define ERR_BAD_ALLOC_LOOKUP	     -7 //!< Cannot allocate VM for lookup table
#define ERR_BAD_ALLOC_PALETTE	     -8 //!< Cannot allocate VM for the color palette
#define ERR_BAD_ALLOC_IMBUF	     -9 //!< Cannot allocate VM for the display buffer
#define ERR_BAD_ALLOC_ZOOM	    -10 //!< Cannot allocate VM for the zoom window
#define ERR_NO_DATA		    -11 //!< No data to display
#define ERR_BAD_DISPLAY_PIPE	    -12 //!< Image display pipe failed
#define ERR_NOT_INITIALIZED	    -13 //!< Windows not created, so cannot draw in them
#define ERR_CANT_GET_FONT	    -14 //!< Cannot allocate font for windows
#define ERR_IMAGE_SIZE_MISMATCH     -15 //!< Image size mismatch

// Data Structures

/*!
  \brief Image vector data structure
*/

typedef struct imagevector {
  short xv;	//!< x coordinate 
  short yv;	//!< y coordinate 
  short color;	//!< color address (-1) for relocate 
} imagevector_t ;

/*!
  \brief Image text data structure
*/

typedef struct imagetext {
  short xt;	  //!< x coordinate 
  short yt;	  //!< y coordinate 
  char  text[80]; //!< text string (80chars max)
  short color;	  //!< color address (-1) for relocate 
} imagetext_t;

/*!
  \brief Action Key data structure
*/

typedef struct KEYACTION {
  void(* action)(int, int, int, int, int );//!< functions to execute when key hit 
  int echo;				   //!< 0/1 to echo character in display 
} keyaction_t ;


// Function Prototypes

int  imageinit(int *, int *, int *, int , int , char *, char *, int , int);
int  createwindows(char *, char *, int, int);
int  imageupdate(int, int, int, int, int);
int  imagedisplay(int , int , int , int , int ,int , int , float *, int);
void imagepalette(int , short *, short *, short *, int );
void imageclose();
void imageerase();
void imagemap(float, float, int);
void imageinstallkey(int, int, void (*)(int, int, int, int, int));
void imageuninstallkey(int);
void imagetext(int, int, char *, int *);
void imagebox(int, int, int, int, int);
void imagecross(int, int, int);
void imagerelocate(int, int);
void imagedraw(int, int, int);
void imagedrawflush(int, int, int);
void vecclear();
void storeclear();
void imagevnull();
void imagetreplay();
void imagevreplay();
void lights(int);
void imagelight(int, char *, int);
int  imageread(int *, int *, char *);
void updateimage(int, int, int, int, int, float *, int, int);
void updatestore();
void updatepan(int, int, int);
void updatesize(int, int);
void newsizesubwin(int, int);
void resizesubwin();
void updatename(char *, int);
void tvimnum(char *, int);
void updatecoords(int, int, int);
void updatebrkpt(int, int);
void brkwrite(char *, float, int);
void resetcolors();
void newcolors(int, int);
void updatenewpal(int, int);
void updatepal(int, int);
int  updatezoom(int, int);
void oldzcursor(int);
void zcursor(int);
void writepix(int, int, int, int);
void keyzoompan(int, int, int);
void keyzoomin(int, int, int, int, int);
void keyzoomout(int, int, int, int, int);
void keypan(int, int, int, int, int);
void keyrecenter(int, int, int, int, int);
void keyzoomprint(int, int, int, int, int);
void keyhelp(int, int, int, int, int);
void zfreeze(int, int, int, int, int);
void nextim(int, int, int, int, int);
void lastim(int, int, int, int, int);
void zpeak(int, int, int, int, int);
void zhairs(int, int, int, int, int);
void vnohair();
int  blackPixel(Display *, int);
int  whitePixel(Display *, int);
int  xtv_refresh(int);
int  xy2index(int, int);

// Utility Functions

void mapimage(int , int , int , int , int , float *, int , int , int , 
	      int , unsigned long *, float *, unsigned long , 
	      unsigned long *, int , unsigned long );
void replicate (int , int , int , int , char *, int , 
		int , int , int , int , int , char *, 
		int , int );
void samplicate(int , int , int , int , char *, int , 
		int , int , int , int , int , char *, 
		int , int );
void duplicate (int , int , int , int , char *, 
		int , int , int , int , int , char *, 
		int , int );
void zeroborder(int , int , int , int , int , int , int , 
		char *, int );
void locate(float [], unsigned long , float , unsigned long *);
void hunt(float [], unsigned long , float , unsigned long *);

// API functions

int  xtvopen(int, int, int, int, int, char *, char *);
void xtvclose();
int  xtvload(float *, int , int , int , int , int , int ,
	     int , float , float , int , int , int );
void xtvcolorld(short *, short *, short *, int);
void bwcmap(short *, short *, short *);
void ibwcmap(short *, short *, short *);


#endif // XTV_H

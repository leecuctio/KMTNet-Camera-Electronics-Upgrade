/*!
  \file xtvutils.c 
  \brief X11 Windows image routines

  \author John Tonry 5/12/88

  Implemented in xvista with various mods - J. Holtzman 5/90-5/91, 96

  Extracted into standalone version and added doxygen markup<br>
  R. Pogge, OSU Astronomy Dept. (pogge@astronomy.ohio.state.edu)<br>
  2005 May 27

*/

#include "xtv.h" // all the header we should need

#ifdef __HAIRS
static Bool hairs_on = False;
static XSegment crshr[4] = {
  {-1, -1, -1, -1},
  {-1, -1, -1, -1},
  {-1, -1, -1, -1},
  {-1, -1, -1, -1},
};
int usehairs = 0;  // flag to tell if we are using full-screen crosshairs
int privcmap = 0;  // flag to determine if we are to use a "private" color map
#endif // __HAIRS

// The various windows, declared in global scope

Display *dpy;   //!< Display pointer 
Window wbase ;  //!< Base window 
Window wimage;	//!< Image window 
Window wpal;    //!< color palette windowd
Window wxyz;	//!< xyz data display windows 
Window wzoom ;	//!< Zoom window 
Window wlgt1;   //!< Status Light 1 window
Window wlgt2;   //!< Status Light 2 window
Window wlgt3;   //!< Status Light 3 window
Window wlgt4;   //!< Status Light 4 window
int screen;     //!< Screen number of display 

// Window information data structure 

XImage *dataimage;	    //!< data image 
XImage *palimage;           //!< palette strip image structure 
XImage *zoomimage;          //!< zoom image 
GC vectorgc, textgc;        //!< Graphics context of the vector and text planes
GC imagegc;                 //!< Image graphics context of the image
#ifdef __HAIRS
GC xorgc;                   //!< Image graphics context of the cross-hairs
#endif

// Define the font used for the xyz display 

Font font;
char *fontname1, *fontname2, **fontpath;
int *nfont;  
XFontStruct *fontinfo;  //!< font info struct
int fontheight;    //!< font height
int fontwidth;     //!< font width

// Global definitions

int ncolors;		     //!< number of image colors used 
int nvcolors;		     //!< number of vector colors used 
unsigned long pixels[256];   //!< color cell addresses allocated 
unsigned long planes[1];     //!< plane mask 
Visual *visual;              //!< window visual (e.g., PseudoColor, TrueColor, etc)
int depth;                   //!< window bit depth (e.g., 16- or 24-bit)
Colormap defcmap;	     //!< Display color map 
XColor cmap[256];	     //!< color cells used 
XColor stcolor[5];	     //!< standard colors status lights, overlay 
XColor palcolors[MAXCOLORS]; //!< complete palette 
XColor vcolor[256];	     //!< vector color palette 
int npalette;		     //!< size of complete palette 
int pal0, pal1;		     //!< palette breakpoints 
float breakpts[256];         //!< break points for the color palette lookup table
int truecolor;               //!< Flag: =1 if a TrueColor visual
int directcolor;             //!< Flag: =1 if a DirectColor visual

unsigned long rmask;         //!< Red color plane mask (from XVisualInfo struct)
unsigned long gmask;         //!< Green color plane mask (from XVisualInfo struct)
unsigned long bmask;         //!< Blue color plane mask (from XVisualInfo struct)

XErrorEvent _XErrorEvent;    //!< X Error Event struct

imagevector_t veclist[MAXVEC];	        //!< Save array for vectors 
int xvlast, yvlast, vcount;		//!< x,y of last vector; number drawn 
int vlastcolor;				//!< color of last vector 

imagetext_t textlist[MAXTEXT];	        //!< Save array for text 
int xtlast, ytlast, tcount;		//!< x,y of last text; number drawn 
int tlastcolor;				//!< color of last text 

int maxwidth, maxheight;                //!< maximum image size 
int width, height;			//!< last size of image part of window 
int resize;				//!< flag for auto resizing of window 
int autozoomout;                        //!< flag for autozoomout of large images 
int zoomsample;                         //!< flag for sample/bin of large images 

int to_program, from_display;		//!< display comm pipe descriptors 
int waiting_for_key = 0;		//!< flag for blocking read 

int store;  //!< storage counter, runs 0..#MAXSTORE

float *data;			//!< address of data (image) array 
char *image[MAXSTORE]; //!< data converted to display bytes 
int nimage[MAXSTORE];           //!< number of bytes in each image 
char *imbuf, *outbuf;	//!< 128k buffer for display 
int yup;			//!< flag = 0/1 for y increasing down/up 
int datw, dath;		       	//!< dimensions of data  array 
int imwidth;			//!< bytes per row of image array=4*((imw+3)/4)
int imw, imh;		       	//!< dimensions of image array 
int winw, winh;			//!< dimensions of image in window 
int zim;			//!< expansion factor of image 
int offx, offy;			//!< original coords of UL of data array 
int datx, daty;			//!< data coords of UL of image portion 
int imx, imy;			//!< image coords of UL of displayed portion 
int winx, winy;			//!< window coords of UL of displayed portion 
int imtv;                       //!< VISTA buffer number  

float *sdata[MAXSTORE];			
int sdatw[MAXSTORE], sdath[MAXSTORE];	
int simwidth[MAXSTORE];		
int simw[MAXSTORE], simh[MAXSTORE];
int swinw[MAXSTORE], swinh[MAXSTORE];
int szim[MAXSTORE];		
int soffx[MAXSTORE], soffy[MAXSTORE];
int sdatx[MAXSTORE], sdaty[MAXSTORE];
int simx[MAXSTORE], simy[MAXSTORE];
int swinx[MAXSTORE], swiny[MAXSTORE];
int simtv[MAXSTORE];
char imname1[MAXSTORE][MAXSTRINGWID];
char imname2[MAXSTORE][MAXSTRINGWID];

int palheight, palwidth, palx, paly;	//!< size and loc of palette subwindow 
float *palbrkpt;			//!< pointer to breakpoint array 
char *palette;			        //!< array with palette values 
short *lookup;				//!< lookup table: data -> color addr 

int lgtheight, lgtwidth, lgtx, lgty[4]; //!< size and loc of light subwindows 

static int lgtstatus[4];
char *uppermess1=NULL;
char *lowermess1=NULL;
char *uppermess2=NULL;
char *lowermess2=NULL;

char xyzstring[NXYZ], numstr[20];       //!< strings used for the cursor data display
int  xyzheight, xyzwidth, xyzx, xyzy;	//!< size and loc of xyz subwindow 
int  mousex, mousey, mousez;		//!< loc and value of mouse 
int  textx, texty[3];		        //!< loc of xyz text 

char *zimage;			        //!< zoom buffer 
int zoomf;				//!< zoom factor 
int zwidth, zheight;			//!< zoom window size 
int lastzoomx, lastzoomy;		//!< location of last update of zoom 

imagevector_t zcursvec[MAXZCURS];	//!< array of zoom cursor vectors 

int whichkey;				//!< which button/key was pressed 
int buttondown;				//!< true if a button is pressed 
int lastx, lasty;			//!< loc where button/key went down 

keyaction_t keyaction[128];  //!< Action keys

// Useful Globals

int TVisOpen = 0;
int fd_for_X = -1;

int imagevalid;

XColor testcolor[200];

int tvinit = 0;
int zfreezeon = 0;
int update=0;

static int whichbreak;

// Initialize X server connection and windows 

int id = 0;

//---------------------------------------------------------------------------
//
// Let the coding begin...
//

/*!
  \brief Initialize the Image

  \param winit width of the window (request on input, actual returned)
  \param hinit height of the window (request on input, actual returned) 
  \param nclrs number of image color cells (requested on input, actual returned)
  \param zfinit initial zoom factor (0 for no zoom window) 
  \param yupinit flag = 0/1 for y increasing down/up 
  \param resourcename name of the X resource for this window
  \param windowname name of the window (to appear on the top bar)
  \param xoff X-axis offset on the desktop on startup
  \param yoff Y-axis offset on the desktop on startup
  
  \return file descriptor for X events on success, negative error codes
  on failure.

  Initializes the window and its resources for the image display and
  sets up the event handler.

*/

int 
imageinit(int *winit, int *hinit, int *nclrs, int zfinit, int yupinit,
	  char *resourcename, char *windowname, int xoff, int yoff)
{
  int pfd[2];                     // pipe descriptors 
  int i, ierr;
  char *option;
  XColor curswcolor, cursbcolor;
  Pixmap csource, cmask;
  char *display;

  int nvisuals, status, nbytes;
  XVisualInfo *vinfo[16];
  XVisualInfo vtemplate;

  // Initialize necessary variable from include file: zimage.h These
  // initializations were removed from the include file so that it can
  // be included in separate files, JAH 5/90

  dpy = NULL;
  wbase = (Window)0;
  wzoom = (Window)0;
  display = NULL;
  npalette = MAXCOLORS;
  vlastcolor = (-1);
  resize = 0;
  autozoomout = 0;
  zoomsample = 1;
  for (i=0; i<MAXSTORE; i++) 
    image[i] = NULL;

  imbuf = NULL;
  outbuf = NULL;
  zim = 0;
  zoomf = DEFZOOMFAC;
  buttondown = 0;
  store = 0;

  zoomf = zfinit;
  yup = yupinit;
  imagevalid = 0;

  // Open the connection to the server, quit on failure 

  if ( ! (dpy = XOpenDisplay(display)) ) {
    printf("Cannot open display %s\n",XDisplayName(display));
    return(ERR_CANT_OPEN_DISPLAY);
  }
  screen = XDefaultScreen(dpy);

  // What kind of visual are we running? 

  visual = DefaultVisual(dpy,screen);
  depth = DisplayPlanes(dpy,screen);
  directcolor = 0;
  truecolor = 0;

#if defined(__cplusplus) || defined(c_plusplus)
  switch (visual->c_class) {
#else
  switch (visual->class) {
#endif
  case PseudoColor:
    printf("Running on a PseudoColor display");
    break;

  case TrueColor:
    printf("Running on a TrueColor display");
    truecolor = 1;
    break;

  case DirectColor:
    printf("Running on a DirectColor display");
    directcolor = 1;
    break;

  default:
    printf("Unrecognized visual - aborting\n");
    break;
  }

#if defined(__cplusplus) || defined(c_plusplus)
  vtemplate.c_class = visual->c_class;
#else
  vtemplate.class = visual->class;
#endif

  *vinfo = XGetVisualInfo(dpy,VisualClassMask,&vtemplate,&nvisuals);

  visual = vinfo[0]->visual;
  depth  = vinfo[0]->depth;
  rmask  = vinfo[0]->red_mask;
  gmask  = vinfo[0]->green_mask;
  bmask  = vinfo[0]->blue_mask;

  // Can we allocate enough colors? If not, use a private colormap 

  defcmap = XDefaultColormap(dpy,screen);
  privcmap = 0;
  if (truecolor) {
    ncolors=256;
    *nclrs = 256;
  } else
    ncolors = *nclrs;

  printf(" with %d colors.\n",ncolors);

  if (!truecolor) { // Try to allocate *nclrs to see if they are available 
    if (XAllocColorCells(dpy, defcmap, 0, planes, 0, pixels, *nclrs) == 0) {
      printf("Insufficient colors in default colormap: switching to private colormap\n");
      defcmap = XCreateColormap(dpy,RootWindow(dpy,screen),visual,AllocNone );
      privcmap= 1;
      if (XAllocColorCells(dpy,defcmap,False,planes,0,pixels,*nclrs) ==0 )
        printf("Error in XAllocColorCells: %d\n",*nclrs);
    } 
    for (i=0 ; i<ncolors; i++) {
      testcolor[i].pixel = pixels[i];
      cmap[i].pixel=pixels[i];
      cmap[i].flags = DoRed | DoGreen | DoBlue;
    }
  } 
 
  // Get color addresses for standard colors for status lights, standard
  // overlay colors (red, white, green, black, blue)

  stcolor[0].red   = 0xffff;  // Red
  stcolor[0].green = 0;
  stcolor[0].blue  = 0;

  stcolor[1].red   = 0xffff;  // White
  stcolor[1].green = 0xffff;
  stcolor[1].blue  = 0xffff;

  stcolor[2].red   = 0;       // Green
  stcolor[2].green = 0xffff;
  stcolor[2].blue  = 0;

  stcolor[3].red   = 0;       // Black
  stcolor[3].green = 0;
  stcolor[3].blue  = 0;

  stcolor[4].red   = 0;       // Blue
  stcolor[4].green = 0;
  stcolor[4].blue  = 0xffff;

  for (i=0;i<5;i++) {
    XAllocColor(dpy,defcmap,stcolor+i);
    stcolor[i].flags = DoRed | DoGreen | DoBlue;
  }

  // Set RGB as standard overlay colors. Default overlay color will be
  // set with image color specification

  nvcolors=4;
  vcolor[1].pixel = stcolor[0].pixel;
  vcolor[2].pixel = stcolor[2].pixel;
  vcolor[3].pixel = stcolor[4].pixel;

  for (i=0;i<nvcolors;i++)
    vcolor[i].flags = DoRed | DoGreen | DoBlue;

  // Get memory for the lookup table 

  if ((lookup = (short *)malloc(1<<17) ) == NULL) {
    printf("Cannot allocate lookup table\n");
    return(ERR_BAD_ALLOC_LOOKUP);
  }
 
  // Get memory for the palette array 

  if ((palette = (char *)malloc(4*MAXPALWIDTH))==NULL) {
    printf("Cannot allocate palette array\n");
    return(ERR_BAD_ALLOC_PALETTE);
  }
  
  // Get memory for the display buffer; ask for X's maximum of 128k 

  if ((imbuf = (char *)malloc(4*MAXSCREENPIX))==NULL) {
    printf("Cannot allocate display buffer\n");
    return(ERR_BAD_ALLOC_IMBUF);
  }
  
  // Create the palette XImage structure 

  palimage = XCreateImage(dpy,visual,depth,ZPixmap,0,palette,
			  MAXPALWIDTH,1,8,0);

  // Create the data XImage structure 

  dataimage = XCreateImage(dpy,visual,depth,ZPixmap,0,
			   imbuf,128,1024,8,0);
  
  // If requested, set parameters for the zoom window 

  if (zoomf > 0) {
    zwidth = zheight = DEFZOOMSIZE;
    lastzoomx = lastzoomy = -100000;
    zoomimage = XCreateImage(dpy,visual,depth,ZPixmap,0,NULL,1,1,8,0);
  }

  // Get the font to be used, and get the information about it 

  fontname1 = XGetDefault(dpy,resourcename,"FontName");
  fontname2 = DEFAULT_FONT2;
  if (fontname1 == NULL) fontname1 = DEFAULT_FONT1;
  if (((fontinfo = XLoadQueryFont(dpy,fontname1)) != NULL)
      ||((fontinfo = XLoadQueryFont(dpy,fontname2)) != NULL) ) {
  } 
  else {
    printf("Cannot open font %s\n",fontname1);
    printf("Put an appropriate font in your .Xdefaults file with index %s.FontName\n",resourcename);
    printf("You will need quit the program and 'xrdb -load .Xdefaults' before this takes effect\n");
    return(ERR_CANT_GET_FONT);
  }
  fontwidth = fontinfo->max_bounds.rbearing - fontinfo->min_bounds.lbearing;
  fontheight = fontinfo->max_bounds.ascent + fontinfo->max_bounds.descent;

  // Initialize keyaction array 

  for(i=0;i<128;i++) {
    keyaction[i].action = NULL;
    keyaction[i].echo = 0;
  }
  keyaction[1].action = keyzoomin;
  keyaction[2].action = keyzoomout;
  keyaction[3].action = keypan;
  keyaction['@'].action = keyrecenter;
  keyaction['r'].action = keyrecenter;
  keyaction['R'].action = keyrecenter;
  keyaction['$'].action = keyzoomprint;
  keyaction['?'].action = keyhelp;
  imageinstallkey('f',0,zfreeze);
  imageinstallkey('F',0,zfreeze);
  imageinstallkey('p',0,zpeak);
  imageinstallkey('P',0,zpeak);
  imageinstallkey('v',0,zpeak);
  imageinstallkey('V',0,zpeak);
#ifdef __HAIRS
  imageinstallkey('h',0,zhairs);
  imageinstallkey('H',0,zhairs);
#endif
  // imageinstallkey('-',0,lastim);
  // imageinstallkey('+',0,nextim);
  // imageinstallkey('=',0,nextim);

  // Open a pipe from parent to itself to use for blocking reads from
  // handler

  if (pipe(pfd) == -1)
    printf("initimage(): Cannot open a pipe for handler\n");
  
  to_program = pfd[1];
  from_display = pfd[0]; 
  
  // Get options for autoresize of windows and/or autozoomout of large
  // images

  option = XGetDefault(dpy,resourcename,"resize");
  if (option != NULL) 
    resize = atoi(option);

  option = XGetDefault(dpy,resourcename,"autozoomout");
  if (option != NULL) 
    autozoomout = atoi(option);

  option = XGetDefault(dpy,resourcename,"zoomsample");
  if (option != NULL) 
    zoomsample = atoi(option);

  // Get options for default window size and maximum window size 

  option = XGetDefault(dpy,resourcename,"width");
  if (option != NULL) 
    *winit = atoi(option);

  option = XGetDefault(dpy,resourcename,"height");
  if (option != NULL) 
    *hinit = atoi(option);

  maxwidth=DEFMAXWIDTH;
  maxheight=DEFMAXHEIGHT;

  option = XGetDefault(dpy,resourcename,"maxwidth");
  if (option != NULL) 
    maxwidth = atoi(option);

  option = XGetDefault(dpy,resourcename,"maxheight");
  if (option != NULL) 
    maxheight = atoi(option);
 
  *winit=MIN(maxwidth,*winit);
  *hinit=MIN(maxheight,*hinit);

  // Create the windows 

  newsizesubwin(*winit,*hinit);
  ierr = createwindows(resourcename,windowname,xoff,yoff);
  if (ierr != 0) return(ierr);
  *winit = width;
  *hinit = height; 
  updateimage(0,0,width,height,width,NULL,0,0);

  tvinit = 1;
  return fd_for_X;
}


/*!
  \brief Create the base window and all its little friends 

  \param resourcename Name of the X-resource file to use
  \param windowname Name of the window (appears on the top bar)
  \param xoff X-axis offset on the desktop
  \param yoff Y-axis offset on the desktop

  \return 0 on success, error codes on failure.

  Creates the base window and all the little subwindows
  that are needed by the image display.

*/

int
createwindows(char *resourcename, char *windowname, int xoff, int yoff)
{
  XColor curswcolor, cursbcolor, backcolor;
  XWMHints  wmhints;
  XSizeHints sizehints;
  XSetWindowAttributes xswa;  //!< set windows attributes
  
  int border_width=2, i;
  Pixmap csource, cmask;
  char *option;
  
  // Define the image cursor and the palette cursor 

  Cursor curs, palcurs;

  // Set background color (resource.backred/backgreen/backblue)

  option = XGetDefault(dpy,resourcename,"backred");
  if (option != NULL) {
    i = atoi(option);
    backcolor.red = i<<8;
  } 
  else
    backcolor.red = 0;

  option = XGetDefault(dpy,resourcename,"backgreen");
  if (option != NULL) {
    i = atoi(option);
    backcolor.green = i<<8;
  } 
  else
    backcolor.green = 0;

  option = XGetDefault(dpy,resourcename,"backblue");
  if (option != NULL) {
    i = atoi(option);
    backcolor.blue = i<<8;
  } 
  else
    backcolor.blue = 0;

  XAllocColor(dpy,defcmap,&backcolor);
  xswa.colormap = defcmap;
  xswa.background_pixel = backcolor.pixel;
  xswa.border_pixel = whitePixel(dpy,screen);
  xswa.backing_store = Always;
  
  sizehints.flags = PPosition | PSize;
  sizehints.width = width;
  sizehints.height = height+XYZHEIGHT; 
  
  // X,Y screen coords of the upper left-hand corner of the main window
  // (resource.x and resource.y)

  option = XGetDefault(dpy,resourcename,"x");
  if (option != NULL) {
    xoff = atoi(option);
    if (xoff < 0) xoff = DisplayWidth(dpy,screen) + xoff - width - 2*border_width;
    sizehints.flags |= (USSize | USPosition);
    sizehints.x = xoff;
  }

  option = XGetDefault(dpy,resourcename,"y");
  if (option != NULL) {
    yoff = atoi(option);
    if (yoff < 0) yoff = DisplayHeight(dpy,screen) + yoff - height - XYZHEIGHT - 2*border_width;
    sizehints.flags |= (USSize | USPosition);
    sizehints.y = yoff;
  }
  
  wbase = XCreateWindow(dpy,RootWindow(dpy,screen),
			xoff,yoff,width,height+XYZHEIGHT,border_width,
			depth,InputOutput,visual,
			CWBackPixel | CWBorderPixel | CWColormap, &xswa);
  if (!wbase) {
    printf( "XCreateWindow failed\n");
    return(ERR_CANT_CREATE_IMAGE_WINDOW);
  }
  XSetWindowColormap(dpy,wbase,defcmap);
  XSetIconName(dpy, wbase, "Ximage");
  XSetStandardProperties(dpy, wbase, windowname, windowname,
			 None, NULL, 0, &sizehints);
  wmhints.input = True;
  wmhints.flags = InputHint;
  XSetWMHints(dpy, wbase, &wmhints);
  XMapWindow(dpy,wbase);
  
  // Create the subwindows 

  // Create the image subwindow inside the main window

  wimage = XCreateSimpleWindow(dpy,wbase,       // Parent window 
			       0,0,             // UL location (nominal) 
			       width,height,    // size (nominal) 
			       0,               // border width 
			       whitePixel(dpy,screen),  // border pixmap 
			       backcolor.pixel); // background pixmap 

  XChangeWindowAttributes(dpy,wimage,CWBackingStore|CWColormap,&xswa);

  // Create the palette subwindow below the image subwindow

  wpal = XCreateSimpleWindow(dpy,wbase,         // Parent window 
			     palx,paly,         // UL location 
			     palwidth,palheight, // size 
			     XYZBORDER,          // border width 
			     whitePixel(dpy,screen),  // border pixmap 
			     blackPixel(dpy,screen)); // background pixmap 

  XChangeWindowAttributes(dpy,wpal,CWBackingStore|CWColormap,&xswa);
  
  // Define the new image cursor 

  curswcolor.pixel = whitePixel(dpy,screen);
  cursbcolor.pixel = blackPixel(dpy,screen);
  XQueryColor(dpy,defcmap,&curswcolor);
  XQueryColor(dpy,defcmap,&cursbcolor);
  
#ifdef __HAIRS
  // If we want full screen crosshairs, define a blank cursor here 

  csource = XCreateBitmapFromData(dpy,wimage,curs_bits,curs_width,curs_height);
  cmask = XCreateBitmapFromData(dpy,wimage,curs_mask_bits,curs_width,curs_height);
  curs = XCreatePixmapCursor(dpy,csource,cmask,
			     &curswcolor,&cursbcolor,curs_x_hot,curs_y_hot);
  XFreePixmap(dpy,csource);
  XFreePixmap(dpy,cmask);
  XDefineCursor(dpy,wimage,curs);
#endif
  
  // Define the palette cursor
  
  csource = XCreateBitmapFromData(dpy,wimage,palcurs_bits,
				  palcurs_width,palcurs_height);

  cmask = XCreateBitmapFromData(dpy,wimage,palcurs_mask_bits,
				palcurs_width,palcurs_height);

  palcurs = XCreatePixmapCursor(dpy,csource,cmask,&curswcolor,&cursbcolor,
				palcurs_x_hot,palcurs_y_hot);

  XDefineCursor(dpy,wpal,palcurs);
  
  XFreePixmap(dpy,csource);
  XFreePixmap(dpy,cmask);

  // xyz subwindow (mouse coords in image space and corresponding data value)

  wxyz = XCreateSimpleWindow(dpy,wbase,xyzx,xyzy,xyzwidth,xyzheight,XYZBORDER,
			     whitePixel(dpy,screen),blackPixel(dpy,screen));
  XChangeWindowAttributes(dpy,wxyz,CWBackingStore|CWColormap,&xswa);

  strcpy(numstr,"BUF");  // actually unused in this implementation, XVista-ism

  // Display status indicator light subwindows, arrayed vertically to
  // the right of the color palette subwindow

  wlgt1 = XCreateSimpleWindow(dpy,wbase,
			      lgtx,lgty[0],lgtwidth,lgtheight,
			      XYZBORDER,
			      whitePixel(dpy,screen),
			      blackPixel(dpy,screen));
  wlgt2 = XCreateSimpleWindow(dpy,wbase,
			      lgtx,lgty[2],lgtwidth,lgtheight,
			      XYZBORDER,
			      whitePixel(dpy,screen),
			      blackPixel(dpy,screen));
  wlgt3 = XCreateSimpleWindow(dpy,wbase,
			      lgtx,lgty[1],lgtwidth,lgtheight,
			      XYZBORDER,
			      whitePixel(dpy,screen),
			      blackPixel(dpy,screen));
  wlgt4 = XCreateSimpleWindow(dpy,wbase,
			      lgtx,lgty[3],lgtwidth,lgtheight,
			      XYZBORDER,
			      whitePixel(dpy,screen),
			      blackPixel(dpy,screen));
  XChangeWindowAttributes(dpy,wlgt1,CWBackingStore|CWColormap,&xswa);
  XChangeWindowAttributes(dpy,wlgt2,CWBackingStore|CWColormap,&xswa);
  XChangeWindowAttributes(dpy,wlgt3,CWBackingStore|CWColormap,&xswa);
  XChangeWindowAttributes(dpy,wlgt4,CWBackingStore|CWColormap,&xswa);
  
  // Create a zoom window if required              

  if (zoomf > 0) {
    sizehints.flags = PPosition | PSize;
    sizehints.width = zwidth*zoomf;
    sizehints.height = zheight*zoomf; 
    
    xoff = 3;
    yoff = 3;

    // optional x,y screen coords of the upper left-hand corner of the
    // zoom window (resource.zoomx and resource.zoomy)

    option = XGetDefault(dpy,resourcename,"zoomx");
    if (option != NULL) {
      xoff = atoi(option);
      if (xoff < 0) xoff = DisplayWidth(dpy,screen) + xoff - zwidth - 2*border_width;
      sizehints.flags |= (USSize | USPosition);
      sizehints.x = xoff;
    }

    option = XGetDefault(dpy,resourcename,"zoomy");
    if (option != NULL) {
      yoff = atoi(option);
      if (yoff < 0) yoff = DisplayHeight(dpy,screen) + yoff - zheight - XYZHEIGHT - 2*border_width;
      sizehints.flags |= (USSize | USPosition);
      sizehints.y = yoff;
    }
    
    wzoom = XCreateWindow(dpy,RootWindow(dpy,screen),
			  xoff,yoff,zwidth*zoomf,zheight*zoomf,1,
			  depth,InputOutput,visual,
			  CWBackPixel | CWBorderPixel | CWColormap, &xswa);

    XSetIconName(dpy, wzoom, "Xzoom");
    if (!wzoom) {
      printf("XCreate failed to make zoom window\n");
      return(ERR_CANT_CREATE_ZOOM_WINDOW);
    }
    XSelectInput(dpy, wzoom, ButtonPressMask|ExposureMask|StructureNotifyMask);
    XSetStandardProperties(dpy, wzoom, "Zoom", "XDisplay Zoom",
			   None, NULL, 0, &sizehints);
    XMapWindow(dpy, wzoom);
  }
  
  // Select inputs from the window 

  // Graphics context for images
 
  imagegc = XCreateGC(dpy, wbase, 0, NULL);
  XSetState(dpy,imagegc,whitePixel(dpy,screen),
	    blackPixel(dpy,screen),GXcopy,AllPlanes);
  
  // Graphics context for drawing vectors on the overlay plane

  vectorgc = XCreateGC(dpy, wbase, 0, NULL);
  XSetState(dpy,vectorgc,whitePixel(dpy,screen),
	    blackPixel(dpy,screen),GXcopy,AllPlanes);
  XSetForeground(dpy, vectorgc, whitePixel(dpy,screen));
  
  // Graphics context for text

  textgc = XCreateGC(dpy, wbase, 0, NULL);
  XSetState(dpy,textgc,whitePixel(dpy,screen),
	    blackPixel(dpy,screen),GXcopy,AllPlanes);
  XSetFont(dpy,textgc,fontinfo->fid);
  XSetFillStyle(dpy,textgc,FillSolid);
  
  // input mask
  
  XSelectInput(dpy, wbase, ExposureMask | LeaveWindowMask |
	       ButtonPressMask | ButtonReleaseMask | StructureNotifyMask |
	       PointerMotionMask | PointerMotionHintMask | KeyPressMask | 
	       ColormapChangeMask);
  XSelectInput(dpy,wimage, ExposureMask);
  
  // Map the subwindows 

  XMapSubwindows(dpy,wbase);
  
  // Flush this pile of X output 

  XFlush(dpy);
  
  // Ask for non-blocking IO on the input from X 

  fd_for_X = ConnectionNumber(dpy);

  return 0;
}

/*!
  \brief close the image window
*/

void
imageclose()
{
  return;
}

/*!
  \brief erase the displayed image

*/

void
imageerase()
{

#ifdef __HAIRS
  if (usehairs && hairs_on) vnohair(); 
#endif
  XClearWindow(dpy,wimage);
  XFlush(dpy);
}

/*!
  \brief update the image (or a subset) on the display

  \param x0 starting X-axis pixel value of the region to update
  \param y0 starting Y-axis pixel value of the region to update
  \param nx number of X-axis pixels in the region
  \param ny number of Y-axis pixels in the region
  \param map flag, if =1, means to remap data values into display bits

  \return 0 on success, error codes on failures.

  Updates all or part of an image on the display.

*/

int
imageupdate(int x0, int y0, int nx, int ny, int map)
{
  int yim;
  if (data == NULL) 
    return(ERR_NO_DATA);
  
  yim = y0 - daty;
  if (yup == 1) 
    yim = imh-1 - (y0-daty);
  
  if (map==1) {
    mapimage(x0,y0,nx,ny,datw,data,x0-datx,yim,imwidth,yup,
	     (unsigned long *)(image[store]),breakpts,ncolors,pixels,
	     dataimage->bits_per_pixel,0);
  } 
  if (zim > 0) {
    yim = winy + zim*(y0-daty-imy);
    if (yup == 1) 
      yim = winy + zim*(imh-1 - (y0+ny-1) - imy + daty);
    
    writepix(zim*(x0-datx-imx)+winx, yim, zim*nx, zim*ny);
  } 
  else {
    yim = winy + (y0-daty-imy)/(-zim);
    if (yup == 1) 
      yim = winy + (imh-1 - (y0+ny-1) - imy + daty)/(-zim);
    
    writepix((x0-datx-imx)/(-zim)+winx, yim, nx/(-zim), ny/(-zim));
  }
  if (zoomf > 0 && !zfreezeon) 
    updatezoom(lastzoomx,lastzoomy);
  
  return 0;
}

/*!
  \brief Display an image

  \param a Input floating image array                   
  \param x0 X-axis origin of the area to be displayed
  \param y0 Y-axis origin of the area to be displayed
  \param nx X-axis size of the area to be displayed
  \param ny Y-axis size of area to be displayed 
  \param awidth Number of pixels per row in a 
  \param xoff X-axis coordinates to be used for pixel (0,0) 
  \param yoff Y-axis coordinates to be used for pixel (0,0) 
  \param color Color plane to load (1=R,2=G,3=B,0=all?)

  Does the dirty work of image display

*/

int
imagedisplay(int x0, int y0, int nx, int ny, int awidth,
	     int xoff, int yoff, float *a, int color)
{
  int i, yim, maxdim, mindim, maxw, maxh;
  unsigned long cmask;

  // First test to see whether any windows have been created 

  if (wbase == 0) {
    printf("Windows not yet created\n");
    return(ERR_NOT_INITIALIZED);
  }

  // Check to see that the image array is large enough for the data 

  if (color==0 || !truecolor) {
    store = store+1>MAXSTORE-1 ? 0 : store+1;
    if (nimage[store] < nx*ny || image[store] == NULL) {
      if (image[store] != NULL) 
	free(image[store]);
      if ((image[store] = 
	  (char *)malloc((dataimage->bits_per_pixel/8)*nx*ny)) == NULL) {
	printf("Cannot allocate image array\n");
	return(ERR_BAD_ALLOC_IMBUF);
      }
      nimage[store] = nx*ny;
    }
    cmask = 0;
  } 
  else {
    if (imw != nx || dath != ny) {
      printf("image size does not match for single color change! %d %d %d %d\n",
	      nimage[store],nx,ny,store);
      return ERR_IMAGE_SIZE_MISMATCH;
    }
    if (color==1)
      cmask=rmask;
    else if (color==2)
      cmask=gmask;
    else if (color==3)
      cmask=bmask;
  }
  
  // Update the display variables 

  updateimage(x0,y0,nx,ny,awidth,a,xoff,yoff);
  yim = 0;
  if (yup == 1) 
    yim = imh - 1;

  mapimage(datx,daty,imw,imh,datw,data,0,yim,imwidth,yup,
	   (unsigned long *)(image[store]),
	   breakpts,ncolors,pixels,
	   dataimage->bits_per_pixel,cmask);
  imagevalid = 1;
  imagevnull();

  // If the image can be zoomed and fit it the display window, do it 

  maxdim = MAX(nx,ny);
  while (maxdim*2 <= MIN(width,height)) {
    updatepan(imw/2,imh/2,1);
    maxdim = maxdim*2;
  }
  
  // If image is too big for display, zoom out if option is set 

  if (autozoomout && (nx>width || ny>height)  ) {
    if (resize) {
      maxw = maxwidth;
      maxh = maxheight;
    } 
    else {
      maxw = width;
      maxh = height;
    }
    while ( (nx/abs(zim))>maxw || (ny/abs(zim))>maxh )  {
      updatepan(imw/2,imh/2,-1);
    }
  }
  
  // Update the size of the display if it is too small 

  if (resize && (width < nx/abs(zim) || height < ny)) {
    width = MIN(maxwidth,MAX(width,nx));
    height = MIN(maxheight,MAX(height,ny));
    updatepan(imw/2,imh/2,0);
    updatesize(width,height);
    if (zim > 0) {
      writepix(winx, winy, zim*imw, zim*imh);
    } 
    else {
      writepix(winx, winy, imw/(-zim), imh/(-zim));
    }
  }
  
  // Otherwise damage the image window so as to get it displayed 
  
  else {
    if (zim > 0) {
      writepix(winx, winy, zim*imw, zim*imh);
    } 
    else {
      writepix(winx, winy, imw/(-zim), imh/(-zim));
    }
  }
  XFlush(dpy);
  return 0;
}

/*!
  \brief Create the color loolup table

  \param zero zero point (min) of the intensity mapping
  \param span span of the intensity mapping (max-min)
  \param ncolors Number of colors to map

  Creates the global breakpts array that is used to quickly map image
  data values into display colors.  The breakpts array contains those
  data values that map into each "color" index in the palette vector.

  The mapping is:
  <pre>
  breakpt[i] = zero + (span/(ncolors-2)) * i
  </pre>
  Note that this algorithm reserves the top
  2 colors in the palette for non-data uses.

*/

void
imagemap(float zero, float span, int ncolors)
{
  float c;
  int i;
  
  palbrkpt = breakpts;
  if (span > 0.0)
    c = span/(float)(ncolors-2);
  else
    c = -span/(float)(ncolors-2);

  for(i=0; i<ncolors-1; i++)
    breakpts[i] = zero + c * i;

}

/*!
  \brief Load the X Windows color palette

  \param n Number of table entries      
  \param r pointer to the red vector
  \param g pointer to the green vector
  \param b pointer to the blue vector
  \param flag 0/1 for image/vector color load 

  Loads the X-windows color palette given a set
  of RGB color vectors.

*/

void
imagepalette(int n, short *r, short *g, short *b, int flag)
{
  int i, k;
  Colormap *list;
  int num;
  
  if (flag == 0) {  // load the image color palette
    for (i=0; i<npalette; i++) {
      k = (i*n) / npalette;
      palcolors[i].red   = 256*(r[k] & 0x00ff);
      palcolors[i].green = 256*(g[k] & 0x00ff);
      palcolors[i].blue  = 256*(b[k] & 0x00ff);
    }
    newcolors(0,npalette-1);
  } 
  else {
    vcolor[0].red   = 256*(r[0] & 0x00ff);
    vcolor[0].green = 256*(g[0] & 0x00ff);
    vcolor[0].blue  = 256*(b[0] & 0x00ff);
    XAllocColor(dpy, defcmap, vcolor);
  }
  
}

/*!
  \brief Install the image cursor action keys

  \param key ASCII code of the key to bind to the action function
  \param echo flag: 0/1 to echo key in x,y,z display 
  \param function() action function to be called when key is pressed.

  The function prototype is
  <pre>
  void action(int x, int y, int xuser, int yuser, int key) 
  </pre>

*/

void
imageinstallkey(int key, int echo, void (* function)(int, int, int, int, int))
{
  keyaction[key].action = function;
  keyaction[key].echo = echo;
}

/*!
  \brief Uninstall an image cursor action key
*/

void
imageuninstallkey(int key)
{ 
  keyaction[key].action = NULL;
  keyaction[key].echo = 0;
}   

/*!
  \brief imagetext - draw text over the image

  \param xuser X-axis coordinate (user coords) of the start of the string
  \param yuser Y-axis coordinate (user coords) of the start of the string
  \param text string with the text
  \param textlen length of the string

  Draw text over an image.
*/

void
imagetext(int xuser, int yuser, char *text, int *textlen)
{
  int zad, x, y;
  
  if (zim > 0) {
    zad = (zim - 1) / 2;
    x = zim * (xuser - imx - datx - offx) + winx + zad;
    if (yup == 0)
      y = winy + zim * (yuser - imy - daty - offy) + zad;
    else
      y = winy + zim * (imh-1 - (yuser - offy - daty) - imy) + zad;
  } else {
    x = (xuser - imx - datx - offx)/(-zim) + winx;
    if (yup == 0)
      y = winy + (yuser - imy - daty - offy)/(-zim);
    else
      y = winy + (imh-1 - (yuser - offy - daty) - imy)/(-zim);
  }
  xtlast = x;
  ytlast = y;
  textlist[tcount].xt = xuser;
  textlist[tcount].yt = yuser;
  text[strlen(text)] = '\0';
  strcpy(textlist[tcount].text,text);
  textlist[tcount].color = -1;
  tcount = MIN(tcount+1,MAXTEXT-1);
  XSetForeground(dpy,textgc,whitePixel(dpy,screen));
  XDrawImageString(dpy,wimage,textgc,x,y,text,*textlen);
  XFlush(dpy);
}

/*!
  \brief Draw a box on the image
  
  \param x X-axis coordinates of the lower corner of the box
  \param y Y-axis coordinates of the lower corner of the box
  \param nx width of the box in X
  \param ny width of the box in Y
  \param color color (palette index) to draw

  Draw a box on the image (vector plane) with the indicated location,
  size and color.
  
*/

void
imagebox(int x, int y, int nx, int ny, int color)
{
  imagerelocate(x,y);
  imagedraw(x,y+ny,color);
  imagedraw(x+nx,y+ny,color);
  imagedraw(x+nx,y,color);
  imagedraw(x,y,color);
}

/*!
  \brief Draw a cross (+) on the image

  \param x X coordinates of the cross center
  \param y Y coordinates of the cross center
  \param r Radius of the cross (pixels)

  Draws a cross (+) on the image (vector plane) centered at the given
  (x,y) coordinates and the given radius.

*/

void
imagecross(int x, int y, int r)
{
  imagerelocate(x-r,y);
  imagedraw(x+r,y,0);
  imagerelocate(x,y-r);
  imagedraw(x,y+r,0);
}

/*!
  \brief Move the overlay vector pointer to user X,Y coordinates

  \param xuser X coordinate in user space
  \param yuser Y coordinate in user space

  Moves the image overlay plane "pen" to a given (X,Y) location in user
  coordinates.  A "relocate" specifies a starting point for a draw.

  \sa imagedraw()
*/

void
imagerelocate(int xuser, int yuser)
{
  int x, y, zad;
  
  if (zim > 0) {
    zad = (zim - 1) / 2;
    x = zim * (xuser - imx - datx - offx) + winx + zad;
    if (yup == 0)
      y = winy + zim * (yuser - imy - daty - offy) + zad;
    else
      y = winy + zim * (imh-1 - (yuser - offy - daty) - imy) + zad;
  } 
  else {
    x = (xuser - imx - datx - offx)/(-zim) + winx;
    if (yup == 0)
      y = winy + (yuser - imy - daty - offy)/(-zim);
    else
      y = winy + (imh-1 - (yuser - offy - daty) - imy)/(-zim);
  }
  
  xvlast = x;
  yvlast = y;
  veclist[vcount].xv = xuser;
  veclist[vcount].yv = yuser;
  veclist[vcount].color = -1;
  vcount = MIN(vcount+1,MAXVEC-1);
}

/*!
  \brief Draw to user coordinates (X,Y) from the last position
  
  \param xuser X-axis coordinate in user space
  \param yuser Y-axis coordinate in user space
  \param color color to use (from the palette)

  Draws a line from the last vector position (previous imagerelocate()
  or imagedraw() call) to the given (X,Y) location with a particular
  palette color.

  The line will not appear immediately on the overlay plane unless the
  display is refreshed.  

  \sa imagerelocate(), imagedrawflush()
*/

void
imagedraw(int xuser, int yuser, int color)
{
  int x, y, zad;
  vlastcolor=-1;
  if (zim > 0) {
    zad = (zim - 1) / 2;
    x = zim * (xuser - imx - datx - offx) + winx + zad;
    if (yup == 0)
      y = winy + zim * (yuser - imy - daty - offy) + zad;
    else
      y = winy + zim * (imh-1 - (yuser - offy - daty) - imy) + zad;
  } 
  else {
    x = (xuser - imx - datx - offx)/(-zim) + winx;
    if (yup == 0)
      y = winy + (yuser - imy - daty - offy)/(-zim);
    else
      y = winy + (imh-1 - (yuser - offy - daty) - imy)/(-zim);
  }
  if (color>nvcolors-1) color=0;
  if (color != vlastcolor) {
    XSetForeground(dpy, vectorgc, vcolor[color].pixel);
    if (_XErrorEvent.serial!=0) 
      printf("loc 1: %d %s", _XErrorEvent.serial,_XErrorEvent.error_code);
    vlastcolor = color;
  }
  XDrawLine(dpy,wimage,vectorgc,xvlast,yvlast,x,y);
  
  xvlast = x;
  yvlast = y;
  veclist[vcount].xv = xuser;
  veclist[vcount].yv = yuser;
  veclist[vcount].color = color;
  vcount = MIN(vcount+1,MAXVEC-1);
  XFlush(dpy);
}

/*!
  \brief Draw and immediately refresh the display

  \param xuser X-axis coordinate in user space
  \param yuser Y-axis coordinate in user space
  \param color color to use (from the palette)

  Draws a line from the last vector position (previous imagerelocate()
  or imagedraw() call) to the given (X,Y) location with a particular
  palette color, and immediately refresh the display.

  \sa imagerelocate(), imagedraw()
*/

void
imagedrawflush(int xuser, int yuser, int color)
{
  imagedraw(xuser,yuser,color);
  XFlush(dpy);
}

/*!
  \brief Clear the overlay plane

  Erases all lines drawn in the image overlay plane
  (resets the overlay vector)

*/

void
vecclear()
{
  int yim;
  
  if (image[store]!=NULL) {
    imagevnull();
    
    if (data == NULL)
      lights(-2);
    else
      lights(2);
    
    if (zim>0) {
      yim = winy + zim*(daty-daty-imy);
      if (yup == 1) 
	yim = winy + zim*(imh-1 - (daty+imh-1) - imy + daty);
      writepix(zim*(datx-datx-imx)+winx, yim, zim*imw, zim*imh);
    } 
    else {
      yim = winy + (daty-daty-imy)/-zim;
      if (yup == 1) 
	yim = winy + (imh-1 - (daty+imh-1) - imy + daty)/-zim;
      writepix((datx-datx-imx)/-zim+winx, yim, imw/-zim, imh/-zim);
    }
    if (zoomf > 0 && !zfreezeon) 
      updatezoom(lastzoomx,lastzoomy);
    xtv_refresh(0);
  }
}

/*!
  \brief clears the image storage (ring) buffer

  Clears all images from the image ring buffer, used to
  store multiple images for blinking.

*/

void
storeclear()
{
  int i;
  for(i=0;i<MAXSTORE;i++)
    if (i!=store) image[i]=NULL;
}

/*!
  \brief Clear (null) the vector and text arrays

*/

void
imagevnull()
{
  vcount = 0;
  tcount = 0;
}

/*!
  \brief redraw text on the overlay plane

*/

void
imagetreplay()
{
  imagetext_t *textp;
  int i,zad, x, y, textlen;
  
  textp = textlist;
  for (i = 0; i < tcount; i++) {
    if (zim > 0) {
      zad = (zim - 1) / 2;
      x = zim * (textp->xt - imx - datx - offx) + winx + zad;
      if (yup == 0)
	y = winy + zim * (textp->yt - imy - daty - offy) + zad;
      else
	y = winy + zim * (imh-1 - (textp->yt - offy - daty) - imy) + zad;
    } 
    else {
      x = (textp->xt - imx - datx - offx)/(-zim) + winx;
      if (yup == 0)
	y = winy + (textp->yt - imy - daty - offy)/(-zim);
      else
	y = winy + (imh-1 - (textp->yt - offy - daty) - imy)/(-zim);
    }
    textlen = strlen(textp->text);
    XSetForeground(dpy,textgc,whitePixel(dpy,screen));
    XDrawImageString(dpy,wimage,textgc,x,y,textp->text,textlen);
    XFlush(dpy);
    xtlast = x;
    ytlast = y;
    textp++;
  }
}

/*!
  \brief Redraw vectors on the overlay plane

*/

void
imagevreplay()
{
  imagevector_t *vecp;
  int i, x, y, zad;

  vecp = veclist;
  zad = (zim - 1) / 2;
  vlastcolor=-1;
  for (i = 0; i < vcount; i++) {
    if (zim > 0) {
      x = zim * (vecp->xv - imx - datx - offx) + winx + zad;
      if (yup == 0)
        y = winy + zim * (vecp->yv - imy - daty - offy) + zad;
      else
        y = winy + zim * (imh-1 - (vecp->yv - offy - daty) - imy) + zad;
    } 
    else {
      x = (vecp->xv - imx - datx - offx)/(-zim) + winx;
      if (yup == 0)
        y = winy + (vecp->yv - imy - daty - offy)/(-zim);
      else
        y = winy + (imh-1 - (vecp->yv - offy - daty) - imy)/(-zim);
    }
    if (vecp->color >= 0) {
      if (vecp->color != vlastcolor) {
        XSetForeground(dpy, vectorgc, vcolor[vecp->color].pixel);
	if (_XErrorEvent.serial!=0) 
	  printf("loc 2: %d %s", _XErrorEvent.serial,_XErrorEvent.error_code);
	vlastcolor = vecp->color;
      }
      XDrawLine(dpy,wimage,vectorgc,xvlast,yvlast,x,y);
    }
    
    xvlast = x;
    yvlast = y;
    vecp++;
  }
}

/*!
  \brief Work the various status "lights" on the display

  \param state status light to operate and its state: +=on/-=off

  The display status lights are numbered 1..4 running from
  top to bottom.  In order:
  <pre>
  Light 1: Input State (-1=Asychronous, +1=waiting for key press)
  Light 2: Image State (-2=no image, 2=image loaded & ready)
  Light 3: Zoom Window State (-3=frozen, +3=active)
  Light 4: Image Zoom State (-4 = normal, +4=zoomed in/out)
  </pre>
  In the normal state the light is green, otherwise it
  is red.
  
  If state=0, it turns all the lights on GREEN (+state)

*/

void
lights(int state)
{
  char string[10];
  int j, i;
  
  if (state == -1 ) imagelight(1,"ASYNC",0);
  if (state == 1  ) imagelight(1,"INPUT",1);
  if (state == -2 ) imagelight(2,"NO DATA",0);
  if (state == 2  ) imagelight(2,"READY",1);
  if (state == -3 ) imagelight(3,"FREEZE",0);
  if (state == 3  ) imagelight(3,"UPDATE",1);
  if (state == -4 ) {
    if (zim==1)
      imagelight(4,"NORM",1);
    else if (zim>0) {
      sprintf(string,"ZOOM+%d",zim);
      imagelight(4,string,0);
    } 
    else {
      sprintf(string,"ZOOM-%d",-zim);
      imagelight(4,string,0);
    }
  }
  if (state == 4 ) 
    imagelight(4,"NORM",1);
  
  if (state == 0) {
    imagelight(1,"INPUT",1);
    imagelight(2,"READY",1);
    imagelight(3,"UPDATE",1);
    imagelight(4,"NORM",1);
  } 
  else {
    i = state > 0 ? state : -1*state;
    lgtstatus[i-1] = state;
  }
}

/*!
  \brief Draw an status light on the display

  \param upper tells which light to draw in (see below)
  \param mess String to be written (null terminated) 
  \param color 0/1 for red/green 

  Draws a status light.  The values of upper
  give which light is to be operated:
  <pre>
  upper = -1 -> redraw all
  upper = 1  -> top light
  upper = 2  -> next from top
  upper = 3  -> next from bottom
  upper = 4  -> bottom light
  </pre>
  Or, graphically
  <pre>
  +-------+
  |   1   |
  +-------+
  |   2   |
  +-------+
  |   3   |
  +-------+
  |   4   |
  +-------+
  </pre>

*/

void
imagelight(int upper, char *mess, int color)
{
  Window *w;
  XColor testcolor;
  int x, y, up, in,i;
  static int oldcolor[3] = {0,0,0};
  
  if (lgtwidth<=10) 
    return;
  
  y = fontheight + (lgtheight-fontheight)/2 - 1;
  
  if (upper == (-1)) {
    if (uppermess1 != NULL) {
      x = (lgtwidth-strlen(uppermess1)*fontwidth)/2;
      XSetForeground(dpy,textgc,stcolor[2*oldcolor[0]].pixel);
      if (_XErrorEvent.serial!=0) 
	printf("loc 3: %d %s", _XErrorEvent.serial,_XErrorEvent.error_code);
      XFillRectangle(dpy,wlgt1,textgc,0,0,lgtwidth,lgtheight);
      XSetForeground(dpy,textgc,stcolor[2*oldcolor[0]+1].pixel);
      if (_XErrorEvent.serial!=0) 
	printf("loc 4: %d %s", _XErrorEvent.serial,_XErrorEvent.error_code);
      XDrawString(dpy,wlgt1,textgc,x,y,uppermess1,strlen(uppermess1));
    }
    if (lowermess1 != NULL) {
      x = (lgtwidth-strlen(lowermess1)*fontwidth)/2;
      XSetForeground(dpy,textgc,stcolor[2*oldcolor[1]].pixel);
      if (_XErrorEvent.serial!=0) 
	printf("loc 5: %d %s", _XErrorEvent.serial,_XErrorEvent.error_code);
      XFillRectangle(dpy,wlgt2,textgc,0,0,lgtwidth,lgtheight);
      XSetForeground(dpy,textgc,stcolor[2*oldcolor[1]+1].pixel);
      if (_XErrorEvent.serial!=0) 
	printf("loc 6: %d %s", _XErrorEvent.serial,_XErrorEvent.error_code);
      XDrawString(dpy,wlgt2,textgc,x,y,lowermess1,strlen(lowermess1));
    }
    if (uppermess2 != NULL) {
      x = (lgtwidth-strlen(uppermess2)*fontwidth)/2;
      XSetForeground(dpy,textgc,stcolor[2*oldcolor[2]].pixel);
      if (_XErrorEvent.serial!=0) 
	printf("loc 7: %d %s", _XErrorEvent.serial,_XErrorEvent.error_code);
      XFillRectangle(dpy,wlgt3,textgc,0,0,lgtwidth,lgtheight);
      XSetForeground(dpy,textgc,stcolor[2*oldcolor[2]+1].pixel);
      if (_XErrorEvent.serial!=0) 
	printf("loc 8: %d %s", _XErrorEvent.serial,_XErrorEvent.error_code);
      XDrawString(dpy,wlgt3,textgc,x,y,uppermess2,strlen(uppermess2));
    }
    if (lowermess2 != NULL) {
      x = (lgtwidth-strlen(lowermess2)*fontwidth)/2;
      XSetForeground(dpy,textgc,stcolor[2*oldcolor[3]].pixel);
      if (_XErrorEvent.serial!=0) 
	printf("loc 9: %d %s", _XErrorEvent.serial,_XErrorEvent.error_code);
      XFillRectangle(dpy,wlgt4,textgc,0,0,lgtwidth,lgtheight);
      XSetForeground(dpy,textgc,stcolor[2*oldcolor[3]+1].pixel);
      if (_XErrorEvent.serial!=0) 
	printf("loc 10: %d %s", _XErrorEvent.serial,_XErrorEvent.error_code);
      XDrawString(dpy,wlgt4,textgc,x,y,lowermess2,strlen(lowermess2));
    }
    XFlush(dpy);
    return;
  }
  
  oldcolor[upper-1] = color;
  x = (lgtwidth-strlen(mess)*fontwidth)/2;
  
  if (upper == 1) {
    w = &wlgt1;
    uppermess1 = mess;
  } 
  else if (upper==2) {
    w = &wlgt2;
    lowermess1 = mess;
  } 
  else if (upper==3) {
    w = &wlgt3;
    uppermess2 = mess;
  } 
  else if (upper==4) {
    w = &wlgt4;
    lowermess2 = mess;
  }
  
  XSetForeground(dpy,textgc,stcolor[2*color].pixel);
  if (_XErrorEvent.serial!=0) 
    printf("loc 11: %d %s", _XErrorEvent.serial,_XErrorEvent.error_code);
  XFillRectangle(dpy,*w,textgc,0,0,lgtwidth,lgtheight);
  
  XSetForeground(dpy,textgc,stcolor[2*color+1].pixel);
  if (_XErrorEvent.serial!=0) 
    printf("loc 12: %d %s", _XErrorEvent.serial,_XErrorEvent.error_code);
  XDrawString(dpy,*w,textgc,x,y,mess,strlen(mess));
  
  XFlush(dpy);
}

/*!
  \brief Blocking read from the display of one character

  \param x User X-axis coordinate where the key was struck
  \param y User Y-axis coordinate where the key was struck
  \param key ASCII code of the key struck

  Puts the cursor on the image and waits for a key to be
  hit (used, e.g., to prompt for user cursor interaction
  on the image).

  Blocking is rude, so do it sparingly.

*/

int
imageread(int *x, int *y, char *key)
{
#if defined(__alpha) || defined(__solaris)
  size_t nbytes = 1;
  ssize_t tmp;
#else
  int nbytes = 1;
  int tmp;
#endif
  
  lights(1);
  waiting_for_key = 1;            // Set flag for interupt routine 
  
  xtv_refresh(0);
  tmp = read(from_display,key,nbytes);
  
  if (tmp > 0) {
    *x = lastx;
    *y = lasty;
    waiting_for_key = 0;
    return 0;
  } 
  else {
    printf("Program-display pipe failure...\n");
    waiting_for_key = 0;
    return(ERR_BAD_DISPLAY_PIPE);
  }
  lights(-1);
}

/*!
  \brief Update the image and window dimension database

  \param x0 X-axis location of the image subsection in the data array
  \param y0 X-axis location of the image subsection in the data array
  \param nx X-axis size of the image subsection in the data array
  \param ny Y-axis size of the image subsection in the data array
  \param awidth number of pixels/line in the data array
  \param a pointer to the floating-point data array
  \param x1 X-axis offset of the data coordinate system
  \param y1 Y-axis offset of the data coordinate system

  Updates the image and window dimension database after a resize or
  other operations that change the size of the window for new images.

*/

void
updateimage(int x0, int y0, int nx, int ny, int awidth,
	    float *a, int x1, int y1)
{
  data = sdata[store] = a;
  datw = sdatw[store] = awidth;
  dath = sdath[store] = ny;

  imw  = simw[store]  = nx;
  imh  = simh[store]  = ny;
  imwidth = simwidth[store] = imw;

  zim  = szim[store]  = 1;

  offx = soffx[store] = x1;
  offy = soffy[store] = y1;

  datx = sdatx[store] = x0;
  daty = sdaty[store] = y0;

  imtv = simtv[store];

  // these parameters need to be updated with each
  // new image

  winw = swinw[store] = MIN(imw,width);
  winh = swinh[store] = MIN(imh,height);

  imx  = simx[store]  = MAX(0,(imw-winw)/2);
  imy  = simy[store]  = MAX(0,(imh-winh)/2);

  winx = swinx[store] = MAX(0,(width-imw)/2);
  winy = swiny[store] = MAX(0,(height-imh)/2);

  strcpy(imname1[store]," ");
  strcpy(imname2[store]," ");
}

/*!
  \brief extract image information from the ring-buffer store

*/

void
updatestore()
{
  data = sdata[store];
  datw = sdatw[store];
  dath = sdath[store];

  imw = simw[store];
  imh = simh[store];
  imwidth = simwidth[store];

  offx = soffx[store];
  offy = soffy[store];
  datx = sdatx[store];
  daty = sdaty[store];

  // update depending on the zoom state

  if (zim>0) {
    winw = MIN(width-winx,zim*(imw-imx));
    winh = MIN(height-winy,zim*(imh-imy));
  } 
  else {
    winw = MIN(width-winx,(imw-imx)/(-zim));
    winh = MIN(height-winy,(imh-imy)/(-zim));
  }

  imtv = simtv[store];

}

/*!
  \brief Update the centering of the image (pan-and-zoom)

  \param xc new image center in X
  \param yc new image center in Y
  \param in zoom: 1=zoom in, -1=zoom out

  Pans the center of the image to user coordinate (xc,yc)
  and either zooms in 1 step (in=1) or zooms out
  1 step (in=-1).

*/

void
updatepan(int xc, int yc, int in)
{
  if (in == 1) {
    if (zim >= 1) 
      zim = MIN(MAXZOOMFACTOR,zim*2);
    else if (zim == -2) 
      zim = 1;
    else 
      zim = zim/2;
  } 
  else if (in == -1) {
    if (zim > 1) 
      zim = zim/2;
    else if (zim == 1) 
      zim = -2;
    else 
      zim = MAX(-MAXZOOMFACTOR,zim*2);
  } 
  else if (in == 2) {
    zim = MAXZOOMFACTOR;
  }

  if (zim > 0) {
    imx = MAX(0,xc-width/(2*zim));
    imy = MAX(0,yc-height/(2*zim));
    winx = MAX(0,zim*(width/(2*zim)-xc));
    winy = MAX(0,zim*(height/(2*zim)-yc));
    winw = MIN(width-winx,zim*(imw-imx));
    winh = MIN(height-winy,zim*(imh-imy));
  } 
  else {
    imx = MAX(0,xc-(-zim*width)/2);
    imy = MAX(0,yc-(-zim*height)/2);
    winx = MAX(0,((-zim*width)/2-xc)/(-zim));
    winy = MAX(0,((-zim*height)/2-yc)/(-zim));
    winw = MIN(width-winx,(imw-imx)/(-zim));
    winh = MIN(height-winy,(imh-imy)/(-zim));
  }
  lights(-4);
}

/*!
  \brief Update all the windows to a new overall size

  \param wid new window width
  \param hgt new window height

  Sets the new width and height for the window and its
  associated subframes.

*/

void
updatesize(int wid, int hgt)
{

  wid = MAX(wid,100);
  hgt = MAX(hgt,100);
  
  XResizeWindow(dpy,wbase,wid,hgt+XYZHEIGHT);
  
  newsizesubwin(wid,hgt);
  resizesubwin();
}

/*!
  \brief Resize subwindows

  \param wid new subwindow width
  \param hgt new subwindow height

*/

void
newsizesubwin(int wid, int hgt)
{
  int i;
  char *pc;
  unsigned short *ps;
  unsigned long *pl;

  // size of image window 
  width = wid;
  height = hgt;

  // xyz window width 
  xyzwidth = MIN(XYZWIDTH*fontwidth,width-30-3*XYZBORDER);
  xyzheight = MIN(height,XYZHEIGHT-2*XYZBORDER);

  // light window width 
  lgtwidth = MIN((MAXMESS)*fontwidth,width);

  // palette window width 
  palwidth = MAX(30,width-xyzwidth-3*XYZBORDER-lgtwidth);

  // readjust xyzwidth to make things fit (if we had to use min palwidth=30)
  xyzwidth = width-lgtwidth-palwidth-3*XYZBORDER;

  if (palimage->bits_per_pixel == 8) {
    pc=(char *)palette;
    for(i=0;i<MIN(MAXPALWIDTH,palwidth);i++)
      *pc++ = cmap[(i*ncolors)/palwidth].pixel & 0xff;
  } 
  else if (palimage->bits_per_pixel == 16) {
    ps=(unsigned short *)palette;
    for(i=0;i<MIN(MAXPALWIDTH,palwidth);i++)
      *ps++ = cmap[(i*ncolors)/palwidth].pixel & 0xffff;
  } 
  else if (palimage->bits_per_pixel == 32) {
    pl=(unsigned long *)palette;
    for(i=0;i<MIN(MAXPALWIDTH,palwidth);i++)
      *pl++ = cmap[(i*ncolors)/palwidth].pixel;
  }

  palheight = xyzheight;
  lgtheight = xyzheight/4;
  xyzx = -1;
  xyzy = height+1;

  palx = xyzx + xyzwidth + XYZBORDER;
  paly = xyzy;

  lgtx = palx + palwidth + XYZBORDER;
  for (i=0; i<4; i++)
    lgty[i] = xyzy + i*XYZHEIGHT/4;
  
  textx = fontwidth;
  for (i=0; i<3; i++)
    texty[i] = (i+1)*fontheight + (i+1)*(xyzheight-3*fontheight)/4-1;

}

/*!
  \brief resize the subwindow 

  Called by higher-level routines to do the actual dirty work

*/

void
resizesubwin()
{
  XMoveResizeWindow(dpy,wimage,0,0,width,height);
  XMoveResizeWindow(dpy,wxyz,xyzx,xyzy,xyzwidth,xyzheight);
  XMoveResizeWindow(dpy,wlgt1,lgtx,lgty[0],lgtwidth,lgtheight);
  XMoveResizeWindow(dpy,wlgt2,lgtx,lgty[2],lgtwidth,lgtheight);
  XMoveResizeWindow(dpy,wlgt3,lgtx,lgty[1],lgtwidth,lgtheight);
  XMoveResizeWindow(dpy,wlgt4,lgtx,lgty[3],lgtwidth,lgtheight);
  XMoveResizeWindow(dpy,wpal,palx,paly,palwidth,palheight);
}

/*!
  \brief update the name that appears on the image display

  \param text string with the new image name
  \param num number of the text string to change (1 or 2)

  Changes one or other of the label strings for the xyz status
  subwindow (displays cursor x,y and corresponding data values).
  <pre>
  num=1 sets imname1[], the top label
  num=2 sets imname2[], the middle label
  </pre>
  Any other values of num are ignored.  

  Note that the bottom label in the xzy subwindow is either the
  position/data readout if the cursor is on the image, or the color
  lookup table value if the cursor is on the color palette subwindow.

*/

void
updatename(char *text, int num)
{
  switch(num) {
  case 1:
    strncpy(imname1[store],text,MAXSTRINGWID-1);
    imname1[store][MAXSTRINGWID-1]=0;
    break;
  case 2:
    strncpy(imname2[store],text,MAXSTRINGWID-1);
    imname2[store][MAXSTRINGWID-1]=0;
    break;
  default:
    return;
    break;
  }
  updatecoords(-1,-1,-1);
}

/*!
  \brief Update the image number of the displayed image

  \param str string with the image number 
  \param n integer version of str

  XVista legacy routines, not implemented here but available if
  someday we want something like it.
*/

void
tvimnum(char *str, int n)
{
  imtv = simtv[store] = n;
  strncpy(numstr,str,MAXSTRINGWID-1);
  numstr[MAXSTRINGWID-1]=0;
  updatecoords(-1,-1,-1);
}

/*!
  \brief Update the cursor x,y coords on the status window

  \param wx X-axis position of the cursor in window space
  \param wy Y-axis position of the cursor in window space
  \param key ASCII code of any action key hit

  Updates the X,Y coords and associated data in the status subwindow
  based on the cursor position and any key that might have been
  struck.  Used as a utility function for any key event action
  functions that will update the contents of the status window.

*/

void
updatecoords(int wx, int wy, int key)
{
  float mousez;
  int x,y,imousez,i;
  int ipix;

  //  If cursor is out of window, just display buffer number and name 
  //  First draw lower string with x, y, value, object name           
  
  if (wx<winx || wx>=(winx+winw) || wy<winy || wy>= (winy+winh)) {
    xyzstring[0] = 0;
  } 
  else {
    x = USERXCOORD(wx);
    y = USERYCOORD(wy);

    if (data == NULL) {
      sprintf(xyzstring,"X=%-4d Y=%-4d         NO DATA",x,y);
    } 
    else { 
      if ((ipix = xy2index(x,y))>0)
	mousez = (float)(*(data+ipix));
      else
	return;  // we're not actually on the image...

      if (ABS(mousez) < 1e6 && ABS(mousez) > 1e-2) {
        imousez = ABS(mousez) + 0.5;
        if (imousez >= 1000) {
          if (mousez < 0) imousez = -imousez;
          sprintf (xyzstring, "X=%-4d Y=%-4d Data=%-8d",x,y,imousez);
        }
        else if (imousez >= 100)
          sprintf(xyzstring, "X=%-4d Y=%-4d Data=%-8.1f",x,y,mousez);
        else if (imousez >= 10)
          sprintf(xyzstring, "X=%-4d Y=%-4d Data=%-8.2f",x,y,mousez);
        else
          sprintf(xyzstring, "X=%-4d Y=%-4d Data=%-8.3f",x,y,mousez);
      } 
      else {
        sprintf(xyzstring, "X=%-4d Y=%-4d Data=%-8.2e",x,y,mousez);
      }
    }

  }

  XSetForeground(dpy,textgc,whitePixel(dpy,screen));
  if (_XErrorEvent.serial!=0) 
    printf("loc 13: %d %s", _XErrorEvent.serial,_XErrorEvent.error_code);

  for (i=strlen(xyzstring); i<NXYZ; i++) 
    xyzstring[i] = ' ';

  xyzstring[NXYZ] = 0;

  if (key >= 0 && key <= 127 && keyaction[key].echo == 1) 
    xyzstring[MAXSTRINGWID-3] = key;

  XDrawImageString(dpy,wxyz,textgc,textx,texty[2],xyzstring,NXYZ);

  //  Draw middle label with contents of imname2[]

  memset(xyzstring,0,sizeof(xyzstring));
  if (data != NULL) 
    strncpy(xyzstring,imname2[store],MAXSTRINGWID-1);

  for (i=strlen(xyzstring); i<NXYZ; i++) 
    xyzstring[i] = ' ';

  xyzstring[MAXSTRINGWID-1] = '\0';

  XDrawImageString(dpy,wxyz,textgc,textx,texty[1],xyzstring,strlen(xyzstring));

  //  Draw top label with contents of imname1[]

  memset(xyzstring,0,sizeof(xyzstring));
  if (data != NULL) 
    strncpy(xyzstring,imname1[store],MAXSTRINGWID-1);

  for (i=strlen(xyzstring); i<NXYZ; i++) 
    xyzstring[i] = ' ';

  xyzstring[MAXSTRINGWID-1] = '\0';

  XDrawImageString(dpy,wxyz,textgc,textx,texty[0],xyzstring,strlen(xyzstring));

  // Show image scaling parameters if the mouse is on the color palette

  if (palwidth > 14*fontwidth) {
    brkwrite(xyzstring,breakpts[0],1);
    XDrawImageString(dpy,wpal,textgc,0,palheight-1,xyzstring,7);
    
    brkwrite(xyzstring,breakpts[ncolors-2],0);
    XDrawImageString(dpy,wpal,textgc,palwidth-7*fontwidth,palheight-1,xyzstring,7);
  }
  XFlush(dpy);
}

/*!
  \brief Display the color palette break point vector value on cursor action

  \param x X-axis coorindate of the cursor in the color palette window
  \param ibut ASCII code of any button pressed

*/

void
updatebrkpt(int x, int ibut)
{
  if (x<0 || x>=ncolors) return;
  if (x == 0) {
    strncpy(xyzstring," z<                  ",40);
    brkwrite(xyzstring+4,breakpts[0],1);
  } 
  else if (x == ncolors-1) {
    strncpy(xyzstring," z>=                  ",40);
    brkwrite(xyzstring+5,breakpts[ncolors-2],1);
  } 
  else {
    strncpy(xyzstring,"       <=z<         ",40);
    brkwrite(xyzstring,breakpts[x-1],0);
    brkwrite(xyzstring+11,breakpts[x],1);
  }
  
  XSetForeground(dpy,textgc,whitePixel(dpy,screen));
  if (_XErrorEvent.serial!=0) 
    printf("loc 15: %d %s", _XErrorEvent.serial,_XErrorEvent.error_code);
  XDrawImageString(dpy,wxyz,textgc,textx,texty[2],xyzstring,strlen(xyzstring));
  
  XFlush(dpy);
#ifdef DEBUG
  printf("Mouse at %d %d, image = %d\n",x,y,*(image+y*datw+x));
#endif
}

/*!
  \brief Fit a floating point number into a 7-character string
  
  \param s character string to create
  \param b floating number to pack into 7 digits
  \param left 1=left pad with blanks

  Converts a floating number (b) into a 7-character
  string with the appropriate format to not overrun
  the string size.  The optional left flag is set
  if the string is to be padded on the left with
  spaces.

*/
void
brkwrite(char *s, float b, int left)
{
  int ib, i, j;
  char buf[8];
  if (ABS(b) < 1e6 && ABS(b) > 1e-2) {
    ib = ABS(b) + 0.5;
    if (ib >= 1000) {
      if (b < 0) ib = -ib;
      sprintf(buf,"%7d",ib);
    }
    else if (ib >= 100)
      sprintf(buf,"%7.1f",b);
    else if (ib >= 10)
      sprintf(buf,"%7.2f",b);
    else
      sprintf(buf,"%7.3f",b);
  } 
  else {
    sprintf(buf,"%7.2e",b);
  }
  if (left) {
    j=0;
    for (i=0;i<7;i++) {
      s[i] = ' ';
      if (buf[i] != ' ') s[j++] = buf[i];
    } 
  } 
  else
    strncpy(s,buf,7);
}

/*!
  \brief Reset the color palette

  Restores the full color palette after compression
  
  \sa newcolors()

*/

void
resetcolors()
{
  newcolors(0,npalette-1);
}

/*!
  \brief Compress the color palette

  \param n1 index of the new Min in the palette
  \param n2 index of the new Max in the palette.

  Repacks the color palette (compresses it) to have the effect of
  changing the image intensity scaling (zeropoint and span), though at a
  sacrifice of bit depth, by re-mapping the intensities to only span
  palette indexes n1..n2 (normally it runs 0..npalette-1).

*/

void
newcolors(int n1, int n2)
{
  int i, k, i1, i2;
  char *pc;
  unsigned short *ps;
  unsigned long *pl;
  float zero, span, c;
  
  n1 = (n1 + npalette) % npalette;
  n2 = (n2 + npalette) % npalette;
  i1 = (n1*ncolors)/npalette;
  i2 = (n2*ncolors)/npalette;
  if (i2 == i1) 
    i2 = (i2+ncolors-1) % ncolors;
  if (i2 < i1) 
    i2 += ncolors;
  
  for (i=MAX(0,i2+1-ncolors);i<MAX(ncolors,i2+1);i++) {
    if (i < i1) 
      k = 0;
    else if (i > i2) 
      k = npalette-1;
    else 
      k = MAX(0,MIN(npalette-1,(npalette*(i-i1))/(i2-i1)));
    cmap[i%ncolors].red   = palcolors[k].red;
    cmap[i%ncolors].green = palcolors[k].green;
    cmap[i%ncolors].blue  = palcolors[k].blue;
  }

  pal0 = n1;
  pal1 = n2;

  if (truecolor) {
    for (i=0; i<ncolors; i++) {
      XAllocColor(dpy,defcmap,cmap+i);
      pixels[i] = cmap[i].pixel;
    }
    
    if (palimage->bits_per_pixel == 8) {
      pc=(char *)palette;
      for(i=0;i<MIN(MAXPALWIDTH,palwidth);i++)
        *pc++ = cmap[(i*ncolors)/palwidth].pixel & 0xff;
    } 
    else if (palimage->bits_per_pixel == 16) {
      ps=(unsigned short *)palette;
      for(i=0;i<MIN(MAXPALWIDTH,palwidth);i++)
        *ps++ = cmap[(i*ncolors)/palwidth].pixel & 0xffff;
    } 
    else if (palimage->bits_per_pixel == 32) {
      pl=(unsigned long *)palette;
      for(i=0;i<MIN(MAXPALWIDTH,palwidth);i++)
        *pl++ = cmap[(i*ncolors)/palwidth].pixel;
    }
    
    // Redraw image 

    imageupdate(datx,daty,imw,imh,1);
    
  } 
  else {
    XStoreColors(dpy,defcmap,cmap,ncolors);
  }

  // Redraw color bar 
  for (i=0;i<palheight;i++)
    XPutImage(dpy,wpal,imagegc,palimage,0,0,0,i,palwidth,1);
  updatecoords(-1,-1,-1);
  XFlush(dpy);
  
}

/*!
  \brief update the color palette after modification

  \param x0  position of breakpoint in the color palette
  \param ibut button pressed (?)

*/

void
updatenewpal(int x0, int ibut)
{
  if (ibut == 2) 
    whichbreak = x0 - pal0;
  else {
    if (ABS(x0-pal0) < ABS(x0-pal1)) 
      whichbreak = 0;
    else 
      whichbreak = 1;
  }

#ifdef DEBUG  
  printf("updatepal: x = %d ibut = %d whichbreak = %d pal0 = %d pal1 = %d\n",
	 x0,ibut,whichbreak,pal0,pal1); 
#endif
  
}

/*!
  \brief Update the palette

  \param x  repack the color palette to this breakpoint
  \param ibut action button hit (?)

*/

void
updatepal(int x, int ibut)
{
  if (ibut == 2)
    newcolors(x-whichbreak,x-whichbreak+pal1-pal0);
  else {
    if (whichbreak==0) {
      newcolors(x,pal1);
    } 
    else {
      newcolors(pal0,x);
    }
  }
#ifdef DEBUG
  printf("updatepal: x = %d ibut = %d whichbreak = %d pal0 = %d pal1 = %d\n",
	 x,ibut,whichbreak,pal0,pal1); 
#endif
}

/*!
  \brief Update the Zoom ("Magnifying Glass") window
  
  \param xw X-axis coordinates of the zoom window center in window space
  \parma yw Y-axis coordinates of the zoom window center in window space

  Updates the zoom (aka "magnifying glass") window view to the
  new center given by (xw,yw) in window-space cooridinates.

*/

static int zoombytes=0;

int
updatezoom(int xw, int yw)
{

  int x, y, i, j, f, n, lc, m;
  int x0, y0, x1, y1, w, h;

  if (xw<winx || xw>=(winx+winw) || yw<winy || yw>= (winy+winh)) 
    return 0;

  // Also, can't do it if we don't have an image...

  if (image[store]==NULL) return 0;

  if (zim > 0) {
    x = (xw-winx)/zim + imx;
    y = (yw-winy)/zim + imy;
  } 
  else {
    x = (-zim)*(xw-winx) + imx;
    y = (-zim)*(yw-winy) + imy;
  }
  
  f = zoomf;
  n = zoomf*zwidth;
  m = zoomf*zheight;
  
  if (zoombytes != n*m) {
    if (zoombytes > 0) 
      free(zimage);
    zoombytes = n*m;
    if ((zimage = (char *)malloc((dataimage->bits_per_pixel/8)*zoombytes))==NULL) {
      printf("Cannot allocate zoom array %d %d\n",
	     dataimage->bits_per_pixel/8,zoombytes);
      return ERR_BAD_ALLOC_ZOOM;
    }
    lastzoomx = lastzoomy = -100000;
    zoomimage->data = zimage;
  }

  replicate(x-zwidth/2,y-zheight/2,imwidth,imh,image[store],
	    f,
	    0,0,n,m,n,zimage,
	    1,
	    dataimage->bits_per_pixel);

  // j is the location of the top left of the central pixel 

  j = n*f*(zheight/2) + f*(zwidth/2);
  zcursor(j);
  
  zoomimage->width = n;
  zoomimage->height = f*zheight;
  zoomimage->bytes_per_line = n*(dataimage->bits_per_pixel/8);
  
  XPutImage(dpy,wzoom,imagegc,zoomimage,0,0,0,0,n,f*zheight);
  
  lastzoomx = xw;
  lastzoomy = yw;

  return 0;
}

/*!
  \brief Old zoom-window cursor position (updatezoom() utility function)

  \param j the location of the top left of the central pixel 

*/

void
oldzcursor(int j)
{
  int i, f, n, a1, a2, a3, a4;
  f = zoomf;
  n = zoomf*zwidth;
  a1 = j - n - 1;
  for(i=0;i<4*(f+1);i++) {
    zimage[a1] = ((i%2) == 0) ?
      blackPixel(dpy,screen) : whitePixel(dpy,screen);
    if (i<f+1) a1++;
    else if (i<2*f+2) a1 += n;
    else if (i<3*f+3) a1--;
    else a1 -= n;
  }
  a1 = j - n + f;
  a2 = a1 - f - 1;
  a3 = a2 + (f+1)*n;
  a4 = a3 + f + 1;
  for(i=0;i<8;i++) {
    zimage[a1] = zimage[a2] = zimage[a3] = zimage[a4] = ((i%2) == 0) ?
      blackPixel(dpy,screen) : whitePixel(dpy,screen);
    a1 -= (n-1);
    a2 -= (n+1);
    a3 += (n-1);
    a4 += (n+1);
  }
}

/*!
  \brief New zoom cursor position (updatezoom() utility function)

  \param j the location of the top left of the central pixel 

*/

void
zcursor(int j)
{
  int i, f, n, a1, a2, a3, a4, nbytes;
  char *zc;
  unsigned short *zs;
  unsigned long *zl;
  unsigned long zpixel;
  
  zc = (char *)zimage;
  zs = (unsigned short *)zimage; 
  zl = (unsigned long *)zimage;
  nbytes = zoomimage->bits_per_pixel / 8;
  
  f = zoomf;
  n = zoomf*zwidth;
  a1 = j - n - 1;
  for(i=0;i<4*(f+1);i++) {
    zpixel = ((i%2) == 0) ? blackPixel(dpy,screen) : whitePixel(dpy,screen);
    if (nbytes==1) 
      *(zc+a1) = zpixel;
    else if (nbytes==2) 
      *(zs+a1) = zpixel;
    else if (nbytes==4) 
      *(zl+a1) = zpixel;
    
    if (i<f+1) a1++;
    else if (i<2*f+2) a1 += n;
    else if (i<3*f+3) a1--;
    else a1 -= n;
  }
  a1 = j - n + f;
  a2 = a1 - f - 1;
  a3 = a2 + (f+1)*n;
  a4 = a3 + f + 1;
  for (i=0;i<8;i++) {
    zpixel = ((i%2) == 0) ? blackPixel(dpy,screen) : whitePixel(dpy,screen);
    if (nbytes==1) 
      *(zc+a1) = *(zc+a2) = *(zc+a3) = *(zc+a4) = zpixel;
    else if (nbytes==2) 
      *(zs+a1) = *(zs+a2) = *(zs+a3) = *(zs+a4) = zpixel;
    else if (nbytes==4) 
      *(zl+a1) = *(zl+a2) = *(zl+a3) = *(zl+a4) = zpixel;
    a1 -= (n-1);
    a2 -= (n+1);
    a3 += (n-1);
    a4 += (n+1);
  }
}

/*!
  \brief Write a portion of the image to the image window

  \param x X-axis coordinate of the region to display in window space
  \param y Y-axis coordinate of the region to display in window space
  \param wid X-axis width in window space
  \param hgt Y-axis height in window space

  A low-level (window space) image subsection display function, usually
  called only by functions that do all the conversion from user space.

  This is where the pixels hit the screen.

*/

void
writepix(int x, int y, int wid, int hgt)
{
  int i0, j0, x0, y0, x1, y1, w0, h0;
  int i, imageoffset;
  
  // First, calculate where the display should actually be 
  // We will not bother clearing the window first (for the time being) 
  // (i0,j0) are the UL pixel of image, (x0,y0) are its location in the window 
  // (x1,y1) are the LR pixel of image + 1 in each dimension 
  
#ifdef DEBUG
  printf("writepix: x, y, w, h = %5d %5d %5d %5d\n",x,y,wid,hgt);
  printf("winx, winw, winy, winh, height: = %5d %5d %5d %5d %5d\n",
	 winx,winw,winy,winh,height);
#endif
  
  // Return if no data available yet 

  if (zim == 0) return;
  
  if (zim > 0) {
    x0 = MAX(zim*(x/zim),winx);
    y0 = MAX(zim*(y/zim),winy);
    x1 = MIN(zim*((x+wid+zim-1)/zim),winx+winw);
    y1 = MIN(height,MIN(zim*((y+hgt+zim-1)/zim),winy+winh));
    
    i0 = (x0-winx)/zim + imx;
    j0 = (y0-winy)/zim + imy;
  } 
  else {
    x0 = MAX(x,winx);
    y0 = MAX(y,winy);
    x1 = MIN(x+wid,winx+winw);
    y1 = MIN(height,MIN(y+hgt,winy+winh));
    
    i0 = (-zim)*(x0-winx) + imx;
    j0 = (-zim)*(y0-winy) + imy;
  }

#ifdef DEBUG
  printf("  x0 = %6d    y0 = %6d\n",x0,y0);
  printf("  x1 = %6d    y1 = %6d\n",x1,y1);
#endif

  if ( x1 <= x0 || y1 <= y0) return;
  
  // (w0,h0) are the size of the displayed piece of image 

  w0 = (x1-x0)/zim;
  h0 = (y1-y0)/zim;

#ifdef DEBUG
  printf("   x = %6d     y = %6d -----\n",x,y);
  printf(" wid = %6d   hgt = %6d\n",wid,hgt);
  printf(" imw = %6d   imh = %6d\n",imw,imh);
  printf("winw = %6d  winh = %6d\n",winw,winh);
  printf(" imx = %6d   imy = %6d\n",imx,imy);
  printf("winx = %6d  winy = %6d\n",winx,winy);
  printf(" zim = %6d ",zim);
  printf("  x0 = %6d    y0 = %6d\n",x0,y0);
  printf("  x1 = %6d    y1 = %6d\n",x1,y1);
  printf("  i0 = %6d    j0 = %6d\n",i0,j0);
  printf("  w0 = %6d    h0 = %6d\n",w0,h0); 
#endif

  dataimage->width = imw;
  dataimage->bytes_per_line = imwidth;

  dataimage->width = (x1-x0);
  dataimage->height = y1 - y0;
  dataimage->bytes_per_line = (x1-x0)*(dataimage->bits_per_pixel/8);
  dataimage->data = (char *)imbuf;

  // Write the appropriately zoomed data into imbuf from image 

  if (zim == 1) {
    duplicate(i0, j0, imwidth, imh, image[store], 0, 
	      0, (x1-x0), y1-y0, (x1-x0), imbuf, 
	      1, dataimage->bits_per_pixel);
  } 
  else if (zim>1) {
    replicate(i0, j0, imwidth, imh, image[store], zim, 0, 0,
	      (x1-x0), y1-y0, (x1-x0), imbuf, 1, 
	      dataimage->bits_per_pixel);
  } 
  else  {
    samplicate(i0, j0, imwidth, imh, image[store], -zim, 0, 0,
	       (x1-x0), y1-y0, (x1-x0),  imbuf, 1, 
	       dataimage->bits_per_pixel);
  }
  
  XPutImage(dpy,wimage,imagegc,dataimage,0,0,x0,y0,(x1-x0),y1-y0); 

  imagevreplay();
  imagetreplay();
  XFlush(dpy);

}

/*!
  \brief Interrupt handler for X Events

  \param signo integer signal code to handle

  This is the function that actually handles actions on window events
  (cursor moving over image, buttons getting pressed, etc.)

*/

int
xtv_refresh(int signo)
{
  Window wmouse;
  Window wroot;
  XEvent event;
  XExposeEvent *expw = (XExposeEvent *)&event;
  XButtonEvent *but = (XButtonEvent *)&event;
  XKeyEvent *key = (XKeyEvent *)&event;
  XPointerMovedEvent *pmove = (XPointerMovedEvent *)&event;
  XColormapEvent *cevent = (XColormapEvent *)&event;
  KeySym ks;
  unsigned int wmask;
  char keystring[KEYLEN];
  XComposeStatus compose_status;
  int x=0, y=0, i, ix, iy, set, iii;
  static int configx=0, configy=0;
  static int ibut;
  unsigned char keycode;
  char keychar;
  char outbuf[32];
  float fcoord;
  
  Window inforoot;
  int infox, infoy;
  unsigned infowidth, infoheight, infoborder, infodepth;

  // do nothing if there is no display initialized

  if (tvinit == 0) return 0;

  // handle events

  whichkey = -1;
  
#define ALL_X_EVENTS   (~0)

  while (
	 // Should we stay in this while loop indefinitely, or return to caller? 
	 (waiting_for_key == 1) ?
	 // Stay in this while loop until key/button press or Config or Expose 
	 (XWindowEvent(dpy,wbase,ALL_X_EVENTS,&event), 1) :
	 // Return to caller as soon as X event queue is emptied 
	 XCheckWindowEvent(dpy,wbase,ALL_X_EVENTS,&event) || 
	 XCheckWindowEvent(dpy,wzoom,ALL_X_EVENTS,&event)  
	 ) {

#ifdef DEBUG
    printf("\ngot event w = %d, x,y,w,h = %d,%d,%d,%d type = %d\n", 
	   expw->window,
	   expw->x,
	   expw->y,
	   expw->width,
	   expw->height,
	   event.type); 
    printf("wbase: %d wimage: %d wzoom: %d\n",wbase,wimage,wzoom);
    switch((int)event.type) {
    case ColormapNotify:
      printf("%d %d %d\n",cevent->send_event, cevent->new, cevent->state);
      XInstallColormap(dpy, defcmap);
    }
#endif

    // If the event came from the zoom window, update it 
    
    if (zoomf != 0 && expw->window == wzoom && imagevalid) {

      switch((int)event.type) {

      case Expose:
	zoomf = ABS(zoomf);
	XGetGeometry(dpy,wzoom,&inforoot,&infox,&infoy,&infowidth,&infoheight,
		     &infoborder,&infodepth);
	zwidth = (infowidth+zoomf-1) / MAX(1,zoomf);
	zheight = (infoheight+zoomf-1) / MAX(1,zoomf);
	if (zoomf >= 0 && !zfreezeon) 
	  updatezoom(mousex,mousey);
	XFlush(dpy);
	break;

      case UnmapNotify:
	zoomf = -ABS(zoomf);
	break;

      case ButtonPress:
	whichkey = but->button;
	if (whichkey == Button2) zoomf = MAX(zoomf-1,1);
	if (whichkey == Button1) zoomf++;
	XGetGeometry(dpy,wzoom,&inforoot,&infox,&infoy,&infowidth,&infoheight,
		     &infoborder,&infodepth);
	zwidth = (infowidth+zoomf-1) / MAX(1,zoomf);
	zheight = (infoheight+zoomf-1) / MAX(1,zoomf);
	if (zoomf > 0 && !zfreezeon) updatezoom(lastzoomx,lastzoomy);
	XFlush(dpy);
      }
    } 

    // Event came from the main window

    else {
      
      // Switch on the type of event 

      switch((int)event.type) {
	
	// WINDOW EXPOSURE EVENT
	
      case Expose:
      case ConfigureNotify:

	//      case VisibilityNotify: 
	//      XQueryWindow(wbase,&winfo); 
	// If the event came from a subwindow, dump it for now 

#ifdef DEBUG
	printf("\nExposure Event: T = %d (E = %d, V = %d); W = %d (I = %d, B = %d);  x = %d y = %d w = %d h = %d n = %d\n",
	       (int)event.type,
	       Expose,
	       VisibilityNotify,
	       expw->window,
	       wimage,wbase,
	       expw->x,
	       expw->y,
	       expw->width,
	       expw->height,
	       expw->count);
#endif

	
	if (abs(expw->x - configx)<10 && abs(expw->y - configy)<10) {
#ifdef DEBUG
	  printf("x-configx=%d y-configy=%d\n",expw->x-configx,
		 expw->y-configy);
#endif
	  break;
	}
        configx=expw->x;
        configy=expw->y;
	
	// If the window was resized, update the subwindow sizes 
#ifdef __HAIRS
        if (usehairs && hairs_on) vnohair();
#endif
	XGetGeometry(dpy,wbase,&inforoot,&infox,&infoy,&infowidth,&infoheight,
		     &infoborder,&infodepth);

	if ((int)(infowidth) != width || (int)(infoheight)!= height+XYZHEIGHT) {
	  newsizesubwin((int)(infowidth),(int)(infoheight)-XYZHEIGHT);
	  resizesubwin();
	  updatepan(imw/2,imh/2,0);
	  XClearWindow(dpy,wbase);
	}
		
        lights(0);
	XFlush(dpy);

#ifdef DEBUG
	printf("Exposure Event Done\n");
#endif
	break;
	
	// BUTTON PRESSED: A mouse button was pressed
	
      case ButtonPress:
	whichkey = but->button;
#ifdef DEBUG
	printf("Button pressed  %d \n", whichkey); 
#endif
	ibut = 0;
	switch(whichkey) {
	case Button1:
	  ibut=1;
	  break;
	case Button2:
	  ibut=2;
	  break;
	case Button3:
	  ibut=3;
	  break;
	}
	lastx = but->x;
	lasty = but->y;
	buttondown = 1;
	
	// The button was pressed in the image window, zoom and center 

	if (but->subwindow == wimage) {
	  if (keyaction[ibut].action != NULL) {
	    (*(keyaction[ibut].action))
	      (but->x,but->y,USERXCOORD(but->x),USERYCOORD(but->y),ibut);
	  }
	}
	
	// The button was pressed in the palette window 

	else if (but->subwindow == wpal) {
#ifdef __HAIRS
          if (usehairs && hairs_on) vnohair();
#endif
	  updatenewpal((npalette*(but->x-palx))/palwidth,ibut);
	}
	
	// Button in light window 3 toggles zfreezeon 

        else if (but->subwindow == wlgt3) {
          zfreezeon = !zfreezeon;
          if (zfreezeon==1)
            lights(-3);
          else
            lights(3);
          update= !zfreezeon;
	  
        }
	
	break;
	
	// BUTTON RELEASED: The button was released
	
      case ButtonRelease:
	buttondown = 0;
	break;
	
	// KEY PRESSED: A Keyboard key was pressed

      case KeyPress:
	
	// Only accept r key from palette subwindow   
	XLookupString(key,keystring,KEYLEN,&ks,&compose_status);
	//        ks = XLookupKeysym(key,0); 
	if (key->subwindow == wpal) {
	  if (keystring[0] == 'r' || keystring[0] == 'R') {
	    newcolors(0,npalette-1);
          }
	  keystring[0] = '\0';
	}
	
	// Ignore keyboard events in subwindows 

	if (key->subwindow != wimage) break;
	
	// Ignore modifier keys 

	if (IsModifierKey(ks)) break ;
	
	// If an arrow key, move the mouse 

	if (IsCursorKey(ks)) {
	  XQueryPointer(dpy,wbase,&wroot,&wmouse,
			&infox,&infoy,&mousex,&mousey,&wmask);
          if (ks == XK_Left) 
	    mousex -= MAX(zim,1);
          else if (ks == XK_Right)
	    mousex += MAX(zim,1);
          else if (ks == XK_Down) 
	    mousey += MAX(zim,1);
          else if (ks == XK_Up) 
	    mousey -= MAX(zim,1);
#ifdef DEBUG
	  printf("Move mouse to %d %d  %d %d %d %d %d\n",
		 mousex,mousey, key->keycode,XK_Left,XK_Right,XK_Down,XK_Up);
#endif
	  XWarpPointer(dpy,None,wimage,0,0,0,0,mousex,mousey);
	  updatecoords(mousex,mousey,-1);
	  XFlush(dpy);
	  break;
	}

	// Get the character typed 

	keychar = keystring[0];
	whichkey = keychar;
	if (whichkey >= 0 && whichkey <= 127 && keyaction[whichkey].action != NULL) {
	  (*(keyaction[whichkey].action))
	    (key->x,key->y,USERXCOORD(key->x),USERYCOORD(key->y),whichkey);
	}
	updatecoords(key->x,key->y,whichkey);
	keystring[0] = '\0';
	
	// waiting_for_key means write into pipe to program 

	if (waiting_for_key) {
	  *outbuf = keychar;
	  lastx = USERXCOORD(key->x);
	  lasty = USERYCOORD(key->y);
	  write(to_program,outbuf,1);
          waiting_for_key = 0;
	} 
	XFlush(dpy);
	break;
	
	// MOUSE MOVED: Mouse movement

      case LeaveNotify:
#ifdef __HAIRS
	if (usehairs && hairs_on) vnohair(); 
#endif
	break;
	
      case MotionNotify:
	// If mouse moved in image window with button down, ignore it 
	if (buttondown && pmove->subwindow == wimage) break;
	XQueryPointer(dpy,wbase,&wroot,&wmouse,
		      &infox,&infoy,&mousex,&mousey,&wmask);
#ifdef __HAIRS
	if (usehairs && wmouse == wimage) {
	  crshr[0] = crshr[2];
	  crshr[1] = crshr[3];
	  crshr[2].x1 = 0; 
	  crshr[2].x2 = width;
	  crshr[2].y1 = crshr[2].y2 = mousey;
	  crshr[3].y1 = 0;
	  crshr[3].y2 = height;
	  crshr[3].x1 = crshr[3].x2 = mousex;
	  if (hairs_on) {
	    XSetForeground(dpy, vectorgc, blackPixel(dpy,screen));
	    if (_XErrorEvent.serial!=0) 
	      printf("loc 17: %d %s", _XErrorEvent.serial,_XErrorEvent.error_code);
	    XDrawSegments(dpy,wimage,vectorgc,crshr,2);
	    XSetForeground(dpy, vectorgc, vcolor[0].pixel);
	    if (_XErrorEvent.serial!=0) 
	      printf("loc 18: %d %s", _XErrorEvent.serial,_XErrorEvent.error_code);
	    writepix(crshr[0].x1,crshr[0].y1,width,1);
	    writepix(crshr[1].x1,crshr[1].y1,1,height);
	    XDrawSegments(dpy,wimage,vectorgc,crshr+2,2);
	  } 
	  else {
	    XSetForeground(dpy, vectorgc, vcolor[0].pixel);
	    if (_XErrorEvent.serial!=0) 
	      printf("loc 19: %d %s", _XErrorEvent.serial,_XErrorEvent.error_code);
	    XDrawSegments(dpy,wimage,vectorgc,crshr+2,2);
	    hairs_on = True;
	  }
	}
#endif      // HAIRS 
	
	if (wmouse == wpal) {
#ifdef __HAIRS
          if (usehairs && hairs_on) vnohair(); 
#endif
	  // If mouse moved in palette window with button down, update palette 
	  if (buttondown) {
	    updatepal((npalette*(mousex-palx))/palwidth,ibut);
	    break;
	  } 
	  else {
	    // If mouse moved in palette window tell what the breakpt is... 
	    updatebrkpt((ncolors*(mousex-palx))/palwidth,ibut);
	    break;
	  }
	}
	
	// Check out current position of mouse 
	
	// If mouse in image window, update coords and zoom 
	if (wmouse == wimage) {
#ifdef DEBUG
	  printf(" mouse is in the image window (x,y)=(%d,%d)\n",
		 mousex,mousey);
#endif
	  updatecoords(mousex,mousey,-1);
	  if (zoomf > 0 && !zfreezeon) {
	    updatezoom(mousex,mousey);
	  }
	}
	break;
      } // end switch on eventtype in base window 
    
    } // end if (event came from base window) 

  } // end of while(1) 

  return 0;

}

/*!
  \brief Zoom/Pan Key Action Function

  \param x X-axis coordinates of the cursor in window space
  \param y Y-axis coordinates of the cursor in window space
  \param inout amount to zoom in (+1) or out (-1)

  Low-level zoom and pan function.

*/

void
keyzoompan(int x, int y, int inout)
{
  int ix, iy;
  if (zim > 0) {
    ix = (x - winx)/zim + imx;
    iy = (y - winy)/zim + imy;
  } 
  else {
    ix = (-zim)*(x - winx) + imx;
    iy = (-zim)*(y - winy) + imy;
  }
  XClearWindow(dpy,wimage);
  XWarpPointer(dpy,None,wimage,0,0,0,0,width/2,height/2);
  updatepan(ix,iy,inout);
  writepix(0,0,width,height);
  if (zoomf > 0 && !zfreezeon) 
    updatezoom(width/2,height/2);
}

/*!
  \brief Zoom In Action Function

  \param x X-axis position of the cursor in window space
  \param y Y-axis position of the cursor in window space
  \param xuser X-axis position of the cursor in user space
  \param yuser Y-axis position of the cursor in user space
  \param key ASCII code of the key pressed

  Action function to zoom in 1 step

*/

void
keyzoomin(int x, int y, int xuser, int yuser, int key)
{
  keyzoompan(x,y,1);
}

/*!
  \brief Zoom Out Action Function

  \param x X-axis position of the cursor in window space
  \param y Y-axis position of the cursor in window space
  \param xuser X-axis position of the cursor in user space
  \param yuser Y-axis position of the cursor in user space
  \param key ASCII code of the key pressed

  Action function to zoom out 1 step

*/

void
keyzoomout(int x, int y, int xuser, int yuser, int key)
{
  keyzoompan(x,y,-1);
}

/*!
  \brief Image Pan Action Function

  \param x X-axis position of the cursor in window space
  \param y Y-axis position of the cursor in window space
  \param xuser X-axis position of the cursor in user space
  \param yuser Y-axis position of the cursor in user space
  \param key ASCII code of the key pressed

  Pan the image to center on the cursor position

*/

void
keypan(int x, int y, int xuser, int yuser, int key)
{
  keyzoompan(x,y,0);
}

/*!
  \brief Restore Original Zoom/Center Action Function

  \param x X-axis position of the cursor in window space
  \param y Y-axis position of the cursor in window space
  \param xuser X-axis position of the cursor in user space
  \param yuser Y-axis position of the cursor in user space
  \param key ASCII code of the key pressed

  De-Zoom and Recenter the image in the window (aka "restore original
  zoom/pan on initial display).

*/

void
keyrecenter(int x, int y, int xuser, int yuser, int key)
{
  int maxdim, maxw, maxh;
  
  zim = 1;
  XClearWindow(dpy,wimage);
  XWarpPointer(dpy,None,wimage,0,0,0,0,width/2,height/2);
  updatepan(imw/2,imh/2,0);
  // If the image can be zoomed and fit it the display window, do it 
  maxdim = MAX(imw,imh);
  while (maxdim*2 <= MIN(width,height)) {
    updatepan(imw/2,imh/2,1);
    maxdim = maxdim*2;
  }
  // If image is too big for display, zoom out if option is set 
  if (autozoomout && (imw>width || imh>height)  ) {
    if (resize) {
      maxw = maxwidth;
      maxh = maxheight;
    } 
    else {
      maxw = width;
      maxh = height;
    }
    while ( (imw/abs(zim))>maxw || (imh/abs(zim))>maxh )  {
      updatepan(imw/2,imh/2,-1);
    }
  }
  
  writepix(0,0,width,height);
  if (zoomf > 0 && !zfreezeon) 
    updatezoom(width/2,height/2);
}

/*!
  \brief Power Zoom/Pan Action Function

  \param x X-axis position of the cursor in window space
  \param y Y-axis position of the cursor in window space
  \param xuser X-axis position of the cursor in user space
  \param yuser Y-axis position of the cursor in user space
  \param key ASCII code of the key pressed

  Power Zoom/Pan - zooms right in on the pixel under
  the cursor, recentering on the display.

*/

void 
keyzoomprint(int x, int y, int xuser, int yuser, int key)
{
  keyzoompan(x,y,2);
}

/*!
  \brief Help Action Function

  \param x X-axis position of the cursor in window space
  \param y Y-axis position of the cursor in window space
  \param xuser X-axis position of the cursor in user space
  \param yuser Y-axis position of the cursor in user space
  \param key ASCII code of the key pressed

  Print the help menu for action keys

*/

void
keyhelp(int x, int y, int xuser, int yuser, int key)
{
  printf("Image window:\n");
  printf("  Left Button:   Zoom IN at location of mouse\n");
  printf("  Center Button: Zoom OUT at location of mouse\n");
  printf("  Right Button:  Pan to location of mouse\n");
  printf("  r key: Redisplay image at original zoom/pan\n");
  printf("\n");
  printf("Color bar: \n");
  printf("  Left or right button drags end of color map down or up\n");
  printf("      i.e., increases the contrast\n");
  printf("  Center mouse button rolls color map\n");
}


/*!
  \brief Freeze Zoom Action Function

  \param x X-axis position of the cursor in window space
  \param y Y-axis position of the cursor in window space
  \param xuser X-axis position of the cursor in user space
  \param yuser Y-axis position of the cursor in user space
  \param key ASCII code of the key pressed

  Routine that freezes the zoom window on one location 
*/

void
zfreeze(int x, int y, int xuser, int yuser, int key)
{
  zfreezeon = !zfreezeon;
  if (zfreezeon == 1)
    lights(-3);
  else
    lights(3);

}

/*!
  \brief Blink to Next Image Action Function

  \param x X-axis position of the cursor in window space
  \param y Y-axis position of the cursor in window space
  \param xuser X-axis position of the cursor in user space
  \param yuser Y-axis position of the cursor in user space
  \param key ASCII code of the key pressed

  Blink forward to the next image in the ring buffer.

*/

void
nextim(int x, int y, int xuser, int yuser, int key)
{
  int yim;

  // advance the store variables

  store = (store+1>MAXSTORE-1 ? 0 : store+1);

  // to the next non-null image

  while (image[store]==NULL)
    store = (store+1>MAXSTORE-1 ? 0 : store+1);

  // update the image metric from the storage buffer

  updatestore();

  // reset the lights

  if (data == NULL)
    lights(-2);
  else
    lights(2);

  // display the image at the current zoom level

  if (zim>0) {
    yim = winy + zim*(daty-daty-imy);
    if (yup) 
      yim = winy + zim*(imh-1 - (daty+imh-1) - imy + daty);
    writepix(zim*(datx-datx-imx)+winx, yim, zim*imw, zim*imh);
  }
  else {
    yim = winy + (daty-daty-imy)/-zim;
    if (yup) 
      yim = winy + (imh-1 - (daty+imh-1) - imy + daty)/(-zim);
    writepix((datx-datx-imx)/(-zim)+winx, yim, imw/(-zim), imh/(-zim));
  }

  // update the zoom window

  if (zoomf > 0 && !zfreezeon) 
    updatezoom(lastzoomx,lastzoomy);

}

/*!
  \brief Blink to Previous Image Action Function

  \param x X-axis position of the cursor in window space
  \param y Y-axis position of the cursor in window space
  \param xuser X-axis position of the cursor in user space
  \param yuser Y-axis position of the cursor in user space
  \param key ASCII code of the key pressed

  Blink back to the previous image in the ring buffer.

*/

void
lastim(int x, int y, int xuser, int yuser, int key)
{
  int yim;

  // roll the store variable back one

  store = (store-1<0 ? MAXSTORE-1 : store-1);

  // and find the last image with something in it

  while (image[store]==NULL)
    store = (store-1<0 ? MAXSTORE-1 : store-1);

  // update the image metric from the storage buffer

  updatestore();

  // reset the lights

  if (data == NULL)
    lights(-2);
  else
    lights(2);

  // display the image at the current zoom state

  if (zim>0) {
    yim = winy + zim*(daty-daty-imy);
    if (yup) 
      yim = winy + zim*(imh-1 - (daty+imh-1) - imy + daty);
    writepix(zim*(datx-datx-imx)+winx, yim, zim*imw, zim*imh);
  }
  else {
    yim = winy + (daty-daty-imy)/-zim;
    if (yup) 
      yim = winy + (imh-1 - (daty+imh-1) - imy + daty)/(-zim);
    writepix((datx-datx-imx)/(-zim)+winx, yim, imw/(-zim), imh/(-zim));
  }

  // update the zoom window

  if (zoomf > 0 && !zfreezeon) 
    updatezoom(lastzoomx,lastzoomy);

}

/*!
  \brief Find Peak Pixel Nearest the Cursor Action Function

  \param x X-axis position of the cursor in window space
  \param y Y-axis position of the cursor in window space
  \param xuser X-axis position of the cursor in user space
  \param yuser Y-axis position of the cursor in user space
  \param key ASCII code of the key pressed

  Finds the peak pixel nearest the cursor and puts the cursor on that
  pixel.  Searches +/-7 pixels around the current location.

*/

void
zpeak(int x, int y, int xuser, int yuser, int key)
{
  int xdata, ydata, xmin, ymin, xmax, ymax, ix, iy, xp, yp, xm, ym;
  float pixel, pmax, *row;

  if (data == NULL) return;
  
  xdata = xuser - offx;
  ydata = yuser - offy;
  xmin = ( xdata-7>datx ? xdata-7 : datx);
  ymin = ( ydata-7>daty ? ydata-7 : daty);
  xmax = ( (xdata+7)<imw+datx ? xdata+7 : imw+datx);
  ymax = ( (ydata+7)<imh+daty ? ydata+7 : imh+daty);
  pmax = *(data+ydata*datw+xdata);
  xp = xdata;
  yp = ydata;
  
  for (iy=ymin; iy<=ymax; iy++){
    row = data + (iy*datw);
    for (ix=xmin; ix<=xmax; ix++) {
      pixel = *(row+ix);
      if ( ((key == (int)'v' || key == (int)'V') && pixel < pmax) ||
           ((key == (int)'p' || key == (int)'P') && pixel > pmax) ) {
        pmax = pixel;
        xp = ix;
        yp = iy;
      }
    }
  }

#ifdef DEBUG
  printf("offx: %d offy: %d datx: %d daty: %d\n",offx,offy,datx,daty); 
  printf("xp: %d yp: %d imx: %d imy: %d\n",xp,yp,imx,imy); 
  printf("datw: %d dath: %d xuser: %d yuser: %d winx: %d winy: %d\n\n",
	 datw, dath, xuser, yuser, winx, winy); 
#endif

  if (zim>0) {
    xm = (xp - datx - imx) * zim + winx;
    ym = (yp - daty - imy) * zim + winy;
    if (yup) 
      ym = (imh-1 - yp - imy + daty) * zim + winy;
    if (zim>1) {
      xm = xm + zim/2 - 1;
      ym = ym + zim/2 - 1;
    }
  } 
  else {
    xm = (xp - datx - imx) / -zim + winx;
    ym = (yp - daty - imy) / -zim + winy;
    if (yup) 
      ym = (imh-1 - yp - imy + daty) / -zim + winy;
  }
#ifdef DEBUG
  printf("xm: %d ym: %d \n",xm,ym);
#endif

  XWarpPointer(dpy,None,wimage,0,0,0,0,xm,ym);
  updatecoords(xm,ym,-1);
  if (zoomf > 0 && !zfreezeon) 
    updatezoom(xm,ym);
  XFlush(dpy);

}

#ifdef __HAIRS
extern int usehairs;

/*!
  \brief Toggle Full-Screen Cross Hairs On/Off Action Function

  \param x X-axis position of the cursor in window space
  \param y Y-axis position of the cursor in window space
  \param xuser X-axis position of the cursor in user space
  \param yuser Y-axis position of the cursor in user space
  \param key ASCII code of the key pressed

  Toggles between the little cross and full-screen cross hairs.

*/

void
zhairs(int x, int y, int xuser, int yuser, int key)
{
  XColor curswcolor, cursbcolor;
  Pixmap csource, cmask;
  Cursor curs;
  
  if (usehairs == 0) {
    XDefineCursor(dpy,
		  wimage,
		  XCreateGlyphCursor(dpy, 
				     fontinfo->fid, 
				     fontinfo->fid,
				     (unsigned int)' ', 
				     (unsigned int)' ',
				     &curswcolor, 
				     &cursbcolor));
    usehairs = 1;
  }
  else {
    vnohair();
    curswcolor.pixel = WhitePixel(dpy,screen);
    XQueryColor(dpy,defcmap,&curswcolor);
    cursbcolor.pixel = BlackPixel(dpy,screen);
    XQueryColor(dpy,defcmap,&cursbcolor);
    csource = XCreateBitmapFromData(dpy,
				    wimage,
				    curs_bits,
				    curs_width,
				    curs_height);
    cmask = XCreateBitmapFromData(dpy,
				  wimage,
				  curs_mask_bits,
				  curs_width,
				  curs_height);
    curs = XCreatePixmapCursor(dpy,
			       csource,
			       cmask,
			       &curswcolor,
			       &cursbcolor,
			       curs_x_hot,
			       curs_y_hot);
    XFreePixmap(dpy,csource);
    XFreePixmap(dpy,cmask);
    XDefineCursor(dpy,wimage,curs);
    usehairs = 0;
  }
}
#endif

//
// tvblink_() used to be here, not anymore  [rwp/osu]
//

#ifdef __HAIRS

/*!
  \brief ...
*/

void
vnohair()
{
#ifdef DEBUG
  printf("vnohair() called\n");
#endif
  crshr[0] = crshr[2];
  crshr[1] = crshr[3];
  crshr[2].x1 = crshr[2].x2 = crshr[2].y1 = crshr[2].y2 = -1;
  crshr[3].y1 = crshr[3].y2 = crshr[3].x1 = crshr[3].x2 = -1;
  XSetForeground(dpy, vectorgc, blackPixel(dpy,screen));
  if (_XErrorEvent.serial!=0) 
    printf("loc 20: %d %s", _XErrorEvent.serial,_XErrorEvent.error_code);
  XDrawSegments(dpy,wimage,vectorgc,crshr,2);
  XSetForeground(dpy, vectorgc, vcolor[0].pixel);
  writepix(crshr[0].x1,crshr[0].y1,width,1);
  writepix(crshr[1].x1,crshr[1].y1,1,height);
#ifdef DEBUG
  printf("vnohair() done\n");
#endif
}
#endif  // HAIRS 

/*!
  \brief Background pixmap (black)

  \param dpy Pointer to the display
  \param screen screen number

*/

int 
blackPixel(Display *dpy, int screen)
{
  if (privcmap)
    return(stcolor[3].pixel);
  else
    return(BlackPixel(dpy,screen));
}

/*!
  \brief Border pixmap (white)

  \param dpy Pointer to the display
  \param screen screen number

*/

int 
whitePixel(Display *dpy, int screen)
{
  if (privcmap)
    return(stcolor[1].pixel);
  else
    return(WhitePixel(dpy,screen));
}

//---------------------------------------------------------------------------

// Utility functions, formerly in zimutil.c

/*!
  \brief Map floating image data into integer display data

  \param x0 X-axis coordinate of origin of image section to map
  \param y0 Y-axis coordinate of origin of image section to map
  \param nx X-axis size of image section to map
  \param ny Y-axis size of image section to map
  \param datw Number of data pixels per row in full image
  \param data array of data to be mapped 
  \param imx0 X-axis origin of the image array
  \param imy0 Y-axis origin of the image array
  \param imw  Number of image pixels per row 
  \param yinv Flag: invert y order of data and image 
  \param image array to receive mapped data 
  \param breakpts lookup table 
  \param nbreak fallback branch table for ambiguous cases 
  \param pixels color cells vector (defined in zimage.h)
  \param bits_per_pixel data precision (bits per pixel), values: 8, 16, or 24
  \param cmask color mask

  Uses the lookup table to map image data values into N-bit display
  values for display.  Unlike an older version of mapimage(), this
  version knows about multiple color planes and color masks (e.g., for
  RGB color planes in a TrueColor visual like a 24-bit display device).

*/

void
mapimage(int x0, int y0, int nx, int ny, int datw,
	 float *data, int imx0, int imy0, int imw,
	 int yinv, unsigned long *image,
	 float *breakpts, unsigned long nbreak,
	 unsigned long *pixels,
	 int bits_per_pixel, unsigned long cmask)
{
  short *l;
  int n, *b;
  unsigned long i;
  char *cim;
  unsigned short *sim;
  unsigned long *lim;
  int k, iminc;
  
  data += datw*y0 + x0;
  iminc = imw - nx;
  if (yinv == 1) 
    iminc -= 2*imw;
  
  i = nbreak/2;

  if (bits_per_pixel == 8) {
    cim = (char *)image + imw*imy0 + imx0;
    for (k=0;k<ny;k++) {
      n = nx;
      while (n--) {
	hunt(breakpts-1,nbreak-1,*data,&i);
	if (i<1) 
	  i=1;
	*cim++ = pixels[i-1] & 0xff;
	data++;
      }
      cim += iminc;
      data += datw - nx;
    }
  } 
  else if (bits_per_pixel == 16) {
    sim = (unsigned short *)image + imw*imy0 + imx0;
    for (k=0;k<ny;k++) {
      n = nx;
      while (n--) {
	hunt(breakpts-1,nbreak-1,*data,&i);
	if (i<1) 
	  i=1;
	*sim++ = pixels[i-1] & 0xffff;
	data++;
      }
      sim += iminc;
      data += datw - nx;
    }
  } 
  else if (bits_per_pixel == 32) {
    lim = (unsigned long *)image + imw*imy0 + imx0;
    if (cmask==0) {
      for (k=0;k<ny;k++) {
	n = nx;
	while (n--) {
	  hunt(breakpts-1,nbreak-1,*data,&i);
	  if (i<1) 
	    i=1;
	  *lim++ = pixels[i-1];
	  data++;
	}
	lim += iminc;
	data += datw - nx;
      }
    } 
    else {
      for (k=0;k<ny;k++) {
	n = nx;
	while (n--) {
	  hunt(breakpts-1,nbreak-1,*data,&i);
	  if (i<1) 
	    i=1;
	  *lim = ((*lim&~cmask) + (pixels[i-1]&cmask)) ;
	  lim++;
	  data++;
	}
	lim += iminc;
	data += datw - nx;
      }
      
    }
  }
}

//
// replicate, samplicate, and duplicate are fast (I hope) routines to
// filling one array from another.
//

/*!
  \brief replicate 

  \param x0 X-axis origin of the source image
  \param y0 Y-axis origin of the source image
  \param w0 width (X-axis size) of source image
  \param h0 height (Y-axis size) of source image
  \param from Source image array
  \param f replication factor
  \param x X-axis origin of the destination image
  \param y Y-axis origin of the destination image
  \param w width (X-axis size) of the destination image
  \param h height (Y-axis size) of the destination image
  \param wto dimensions of the destination image
  \param to Destination image array
  \param fill Flag: 1=zero rest of the to array
  \param bits_per_pixel data precision of the arrays

  Fills the destination array with an arbitrary (square) repetition
  of each source pixel into NxN pixels in the destination array

  Fill array "to" with a piece of "from", each pixel mapping to fxf pixels
  If fill != 0, zero any uncovered piece of destination array 

  Note, this version uses memmove() instead of bcopy() since the latter
  is now officially deprecated.

*/

void
replicate(int x0, int y0, int w0, int h0, char *from,
	  int f, int x, int y, int w, int h, int wto,
	  char *to, int fill, int bits_per_pixel)
{
  char *s, *d;
  int k, n, i;

  int i0,i1,j0,j1,j;
  int nbytes;

  nbytes = bits_per_pixel/8;
  j0 = MAX(0,y0);
  j1 = MIN(h0,y0+h/f);
  i0 = MAX(0,x0);
  i1 = MIN(w0,x0+w/f);
  for (j=j0; j<j1; j++) {
    s = from + nbytes*(w0*j + i0);
    d = to + nbytes*(wto*(f*(j-y0)+y) + x + f*(i0-x0));
    i = i1 - i0;
    n = f;
    while (i--) {
      k = n;
      // while (k--) *d++ = *s;
      while (k--) {
	memmove(d,s,nbytes);
        // bcopy(s,d,nbytes);
        d+=nbytes;
      }
      s+=nbytes;
    }

    i = f-1;
    n = nbytes*f*(i1-i0);
    s = d - nbytes*(f*(i1-i0));
    d = s + nbytes*wto;

    while (i--) {
      memmove(d,s,n);
      // bcopy(s,d,n);
      d += wto*nbytes;
    }

  }
  
  if (fill != 0)
    zeroborder(f*x0, f*y0, f*w0, f*h0, w, h, wto, to, nbytes);

}

/*!
  \brief samplicate an array (sample instead of replicate)

  \param x0 X-axis origin of the source image
  \param y0 Y-axis origin of the source image
  \param w0 width (X-axis size) of source image
  \param h0 height (Y-axis size) of source image
  \param from Source image array
  \param f sampling factor
  \param x X-axis origin of the destination image
  \param y Y-axis origin of the destination image
  \param w width (X-axis size) of the destination image
  \param h height (Y-axis size) of the destination image
  \param wto dimensions of the destination image
  \param to Destination image array
  \param fill Flag: 1=zero rest of the to array
  \param bits_per_pixel data precision of the arrays

  fills the destination array with an arbitrary (square) sampling
  sampling of each NxN source pixels into the destination array

 */

void
samplicate(int x0, int y0, int w0, int h0, char *from,
	  int f, int x, int y, int w, int h, int wto,
	  char *to, int fill, int bits_per_pixel)
{
  char *s, *d;
  int k, n, i;
  int i0,i1,j0,j1,j;
  int nbytes;
  nbytes = bits_per_pixel/8;
  j0 = MAX(0,y0);
  j1 = MIN(h0,y0+f*h);
  i0 = MAX(0,x0);
  i1 = MIN(w0,x0+f*w);
  for (j=j0; j<j1; j+=f) {
    s = from + nbytes*(w0*j + i0);
    d = to + nbytes*(wto*((j-y0)/f+y) + x + (i0-x0)/f);
    for (i=i0; i<i1; i+=f) {
      memmove(d,s,nbytes);
      //bcopy(s,d,nbytes);
      d+=nbytes;
      s+=f*nbytes;
    }
  }

  if (fill != 0) 
    zeroborder(x0/f, y0/f, w0/f, h0/f, w, h, wto, to, nbytes);
}

/*!
  \brief duplicate pixel replication mapping without expansion/compression

  \param x0 X-axis origin of the source image
  \param y0 Y-axis origin of the source image
  \param w0 width (X-axis size) of source image
  \param h0 height (Y-axis size) of source image
  \param from Source image array
  \param x X-axis origin of the destination image
  \param y Y-axis origin of the destination image
  \param w width (X-axis size) of the destination image
  \param h height (Y-axis size) of the destination image
  \param wto dimensions of the destination image
  \param to Destination image array
  \param fill Flag: 1=zero rest of the to array
  \param bits_per_pixel data precision of the arrays

  The same as replicate with no expansion or compression 

*/

void
duplicate(int x0, int y0, int w0, int h0, char *from,
	  int x, int y, int w, int h, int wto, char *to, 
	  int fill, int bits_per_pixel)
{
  int i0,i1,j0,j1,j,k,l,nbytes;
  unsigned long *val;
  j0 = MAX(0,y0);
  j1 = MIN(h0,y0+h);
  i0 = MAX(0,x0);
  i1 = MIN(w0,x0+w);
  nbytes=bits_per_pixel/8;
  for (j=j0; j<j1; j++) {
    memmove(to + nbytes*(wto*(j-y0+y) + x + i0-x0), 
	    from + nbytes*(w0*j + i0),   
	    nbytes*(i1 - i0));
  }
  if (fill != 0) 
    zeroborder(x0, y0, w0, h0, w, h, wto, to, nbytes);
}

/*!
  \brief fill border with zeros

  \param x0 X-axis origin of the source image
  \param y0 Y-axis origin of the source image
  \param w0 width (X-axis size) of source image
  \param h0 height (Y-axis size) of source image
  \param w width (X-axis size) of the destination image
  \param h height (Y-axis size) of the destination image
  \param wto dimensions of the destination image
  \param to Destination image array
  \param nbytes

*/

void
zeroborder(int x0, int y0, int w0, int h0, 
	   int w, int h, int wto, 
	   char *to, 
	   int nbytes)
{
  int i;
  if (y0 < 0) {
    for (i=0; i<(-y0); i++) 
      bzero(to+nbytes*(i*wto), w*nbytes);
  }
  if (h > h0-y0) {
    for (i=h0-y0; i<h; i++) 
      bzero(to+nbytes*(i*wto), w*nbytes);
  }
  if (x0 < 0) {
    for (i=0; i<h; i++) 
      bzero(to+nbytes*(i*wto), -x0*nbytes);
  }
  if (x0+w > w0) {
    for (i=0; i<h; i++) 
      bzero(to+nbytes*(i*wto+w0-x0), (x0+w-w0)*nbytes);
  }
}

/*!
  \brief locate index of x in array xx

  \brief xx data vector
  \brief n length of data vector xx
  \brief x value in xx to find
  \brief j index of x in xx

*/

void 
locate(float xx[], unsigned long n, float x, unsigned long *j)
{
  unsigned long ju,jm,jl;
  int ascnd;
  jl=0;
  ju=n+1;
  ascnd=(xx[n] >= xx[1]);
  while (ju-jl > 1) {
    jm=(ju+jl) >> 1;
    if (x >= xx[jm] == ascnd)
      jl=jm;
    else
      ju=jm;
  }
  if (x == xx[1]) 
    *j=1;
  else if (x == xx[n]) 
    *j=n-1;
  else 
    *j=jl;
}

/*!
  \brief hunt for nearest left index of x in array xx

  \param xx  data vector
  \param n   length of the data vector xx
  \param x   data value to find in the vector
  \param jlo (returned) index of x

*/

void 
hunt(float xx[], unsigned long n, float x, unsigned long *jlo)
{
  unsigned long jm,jhi,inc;
  int ascnd;

  ascnd=(xx[n] >= xx[1]);
  if (*jlo <= 0 || *jlo > n) {
    *jlo=0;
    jhi=n+1;
  } 
  else {
    inc=1;
    if (x >= xx[*jlo] == ascnd) {
      if (*jlo == n) return;
      jhi=(*jlo)+1;
      while (x >= xx[jhi] == ascnd) {
	*jlo=jhi;
	inc += inc;
	jhi=(*jlo)+inc;
	if (jhi > n) {
	  jhi=n+1;
	  break;
	}
      }
    } 
    else {
      if (*jlo == 1) {
	*jlo=0;
	return;
      }
      jhi=(*jlo)--;
      while (x < xx[*jlo] == ascnd) {
	jhi=(*jlo);
	inc <<= 1;
	if (inc >= jhi) {
	  *jlo=0;
	  break;
	}
	else 
	  *jlo=jhi-inc;
      }
    }
  }
  while (jhi-(*jlo) != 1) {
    jm=(jhi+(*jlo)) >> 1;
    if (x >= xx[jm] == ascnd)
      *jlo=jm;
    else
      jhi=jm;
  }
  if (x == xx[n]) 
    *jlo=n-1;
  if (x == xx[1]) 
    *jlo=1;
}

/*!
  \brief Convert (x,y) user coordinates into data vector index

  \param xuser user X coordinate
  \param yuser user Y coordinate
  \return array index corresponding to (x,y), or -1 if 
  out of bounds

*/

int
xy2index(int xuser, int yuser)
{
  int npix;
  int ipix;

  npix = imw*imh;
  ipix = (yuser-offy)*datw + (xuser-offx);
  if (ipix < 0 || ipix > npix)
    return -1;
  else 
    return ipix;
}

//
// clientutils - client app utilities go here
//

/*!
  \file clientutils.c
  \brief Client application utility functions

  Because they have to go somewhere...

  \author R. Pogge, OSU Astronomy Dept. (pogge@astronomy.ohio-state.edu)
  \date 2005 May 30
*/

#include "client.h" // custom client application header 

//---------------------------------------------------------------------------

/*!
  \brief Initialize an image parameters data structure

  \param img pointer to an #img_params data structure

  Initializes an image parameters data structure, nulling
  all pointers and data values.

*/

void
InitImgPars(img_t *img) 
{
  img->data = NULL;
  img->nx = 0;
  img->ny = 0;
  img->haveImage = 0;
  strcpy(img->file,"NONE");
  strcpy(img->fullname,"NONE");
  strcpy(img->object,"NONE");
}

/*!
  \brief Initialize a display parameters data structure

  \param disp pointer to an #disp_params data structure

  Initializes a display parameters data structure, setting
  up sensible defaults

*/

void
InitDispPars(disp_t *disp) 
{
  strcpy(disp->AppName,"xtv");
  strcpy(disp->WinName,"XTV Image Display");
  disp->NX = 800;
  disp->NY = 800;
  disp->NColors = 256;
  disp->Zoom = 4;
  disp->Flip = 0;
  disp->z1 = 0.0;
  disp->z2 = 0.0;
  disp->cmap = BW;
  bwcmap(disp->r,disp->g,disp->b);
}

/*!
  \brief load a FITS image into memory

  \param img pointer to a #img_params data structure
  \param fitsfile full name of the FITS format file to read
  \param reply string to contain any messages from the process
  \return 0 on success, -1 if errors

  Opens the named FITS format image file readonly and attempts to read
  it into the data array in the img struct.  Also loads the image
  dimensions, filename, object name (if an OBJECT card is present in the
  header), and sets the #img_params::haveImage flag true.

  Calls the HEASARC cfitsio library routines to do the dirty work.

*/

int
ReadFITSFile(img_t *img, char *infile, char *reply)
{ 

  fitsfile *infptr;

  long inaxis=2;
  long inaxes[2];
  int npixels;
  long fpixel = 1;
  int nfound, anynull;
  int status = 0;
  float nullval = 0.0;
  char comment[FLEN_COMMENT];
  char status_str[FLEN_STATUS];

  // Try to open the FITS file

  if (client.Debug) printf("opening FITS file %s\n",infile);

  if (fits_open_file(&infptr, infile, READONLY, &status)) {
    fits_get_errstatus(status, status_str);
    sprintf(reply,"Cannot open FITS file %s - %s", infile, status_str);
    img->haveImage = 0;
    return -1;
  }
  
  strcpy(img->fullname,infile);

  // Read in the image header

  if (fits_read_keys_lng(infptr, "NAXIS", 1, 2, inaxes, &nfound, &status)) {
    fits_get_errstatus(status, status_str);
    sprintf(reply,"Cannot read FITS header of %s - %s",infile,status_str);
    fits_close_file(infptr,&status);
    img->haveImage = 0;
    return -1;
  }

  npixels  = inaxes[0] * inaxes[1];      /* number of pixels in the image */

  if (client.Debug) printf("done: naxis1=%d naxis2=%d npixels=%d\n",inaxes[0],
			   inaxes[1],npixels);

  // Allocate memory for the data as a 1-D floating array

  if (img->data > 0)
    free(img->data);

  if (client.Debug) printf("allocating %d bytes of memory\n",npixels*sizeof(float));

  img->data = (float*)(calloc(npixels,sizeof(float)));
  if (img->data == NULL) {
    sprintf(reply,"Cannot allocate memory for %s",infile);
    fits_close_file(infptr,&status);
    img->haveImage = 0;
    return -1;
  }
  img->nx = (int)(inaxes[0]);
  img->ny = (int)(inaxes[1]);

// Read in the image

  if (client.Debug) printf("reading image...\n");
  if (fits_read_img(infptr, TFLOAT, fpixel, npixels, &nullval,
                    img->data, &anynull, &status)) {
    fits_get_errstatus(status, status_str);
    sprintf(reply,"Cannot read FITS file %s - %s",infile,status_str);
    fits_close_file(infptr,&status);
    img->haveImage = 0;
    free(img->data);
    return -1;
  }
  if (client.Debug) printf("done.\n");

  img->haveImage = 1;

  // If there is a FILENAME header card, read it into img->file, otherwise use the full filename

  if (fits_read_key(infptr,TSTRING,"FILENAME",img->file,comment,&status))
    strcpy(img->file,infile);
    
  // If there is an OBJECT header card, read it into img->object, otherwise leave as NONE

  if (fits_read_key(infptr,TSTRING,"OBJECT",img->object,comment,&status))
    strcpy(img->object,"NONE");

  // All done with the FITS file, close it

  fits_close_file(infptr, &status);

  return 0;

}

/*!
  \brief Compute the mean of the image

  \param img pointer to an img_params data structure
  \param step interval to step through the image (1=all pixels)
  \return 0 on success, -1 on errors

  Computes the mean in the image.  For speed, an optional "step" can
  be specified to step through the image every step-th pixel.  For
  example, for computing a default display level, one might call
  ImageMean to compute the mean for every 9th pixel.

*/

int
ImageMean(img_t *img, int step)
{
  int i;
  int npix;
  int nsamp = 0;

  if (!img->haveImage)
    return -1;

  npix = img->nx * img->ny;

  // compute image mean using every step-th pixels

  img->mean = 0.0;
  for (i=0; i<npix; i+=step) {
    img->mean += img->data[i];
    nsamp++;
  }
  if (nsamp > 0)
    img->mean = img->mean / float(nsamp);
  else
    return -1;

  return 0;
}


/*!
  \brief Print the current display parameters

  \param disp pointer to a #disp_params data structure 

  Prints the contents of the #disp_params data structure
  describing the image display parameters to stdout.
  Meant as an engineering interfrace.

*/

void
DispInfo(disp_t *disp)
{
  printf("Image Display Parameters:\n");
  printf("  App Resource Name: %s\n",disp->AppName);
  printf("  Window Title: %s\n",disp->WinName);
  printf("  Display Size: %d x %d\n",disp->NX,disp->NY);
  printf("  Number of Colors: %d\n",disp->NColors);
  if (disp->Zoom>0)
    printf("  Zoom Window magnification factor: %d\n",disp->Zoom);
  else
    printf("  Zoom Window disabled\n");
  if (disp->Flip)
    printf("  Image Parity: Flipped (Y increases Up)\n");
  else
    printf("  Image Parity: Normal (Y increases Down)\n");
  
  printf("Display Levels:\n");
  printf("  Min Data: %.2f\n",disp->z1);
  printf("  Max Data: %.2f\n",disp->z2);

  switch(disp->cmap) {
  case BW:
    printf("  B&W Color Map\n");
    break;
  case IBW:
    printf("  Inverse B&W Color Map\n");
    break;
  default:
    printf("  Color Map UNKNOWN\n");
    break;
  }
  printf("XWindows Event File Descriptor: %d\n",disp->FD);
  printf("\n");
}

/*!
  \brief Print the current image parameters

  \param img pointer to a #img_params data structure 

  Prints the contents of the #img_params data structure
  describing the image currently loaded into memory.
  Meant as an engineering interfrace.

*/

void
ImageInfo(img_t *img)
{
  if (img->haveImage) {
    printf("Image Parameters:\n");
    printf("  Image File: %s (%s)\n",img->file,img->fullname);
    printf("  Image Size: %d x %d pixels\n",img->nx,img->ny);
    printf("  Object Name: %s\n",img->object);
    // more later...
    printf("\n");
  }
  else {
    printf("No images connected\n");
    printf("\n");
  }
}

/*!
  \brief Generate a synthetic image and fill it with data

  \param img pointer to an img_params data structure
  \param nx size of the image in X
  \param ny size of the image in Y
  \param bkg data value to fill the array
  \return 0 on success, -1 on errors

  Computes the mean in the image.  For speed, an optional "step"
  can be specified to step through the image every step-th pixel.
  For example, for computing a default display level, one might
  call ImageMean to compute the mean for every 9th pixel.

*/

int
FakeImage(img_t *img, int nx, int ny, float bkg)
{
  int npix;
  int i;

  if (nx==0 || ny==0)
    return -1;

  npix  = nx * ny;

  // Allocate memory for the data as a 1-D floating array

  if (img->data > 0)
    free(img->data);

  img->data = (float*)(calloc(npix,sizeof(float)));
  if (img->data == NULL) {
    printf("Cannot allocate memory for image\n");
    img->haveImage = 0;
    return -1;
  }
  img->nx = nx;
  img->ny = ny;

  for (i=0; i<npix;i++)
    img->data[i] = bkg;

  img->haveImage = 1;
  strcpy(img->object,"Fake Image");

  return 0;

}

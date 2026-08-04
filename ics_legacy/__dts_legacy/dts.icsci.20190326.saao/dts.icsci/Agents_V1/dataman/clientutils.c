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

  disp->doDisplay = 0;  // default: no autodisplay

}

/*!
  \brief load a FITS image into memory

  \param img pointer to a #img_params data structure
  \param infile full name of the FITS format file to read
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
  printf("  AutoDisplay %s\n",
	 ((disp->doDisplay) ? "Enabled" : "Disabled"));
  
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

/*!
  \brief Display an image on the XTV display

  \param img pointer to an #img_params data structure with FITS data
  \param disp pointer to an #disp_params data structure
  \param fname name of the image to display (must include full path)
  \param reply string for any messages generated by this function

  \return 0 on success, -1 on errors.  Success or error messages
  are in reply.

  Opens the named file readonly, reads it into the display memory,
  then displays it on the XTV image display.

*/

int
DisplayImage(img_t *img, disp_t *disp, char *fname, char *reply)
{
  char fitsfile[128];

  // Make sure we have a display to work with

  if (!disp->doDisplay) {
    strcpy(reply,"Image Display Not Enabled");
    return -1;
  }

  // Read in the image (handles all memory allocation issues)
  
  if (ReadFITSFile(img,fname,reply)<0) {
    strcat(reply," - Cannot display image");
    return -1;
  } 
  strcpy(img->fullname,fname);

  if (client.Debug) printf("displaying image...\n");

  xtvload(img->data,img->nx,img->ny,img->nx,0,0,1,1,
	  disp->z1,disp->z2,disp->Flip,1,0);

  if (client.Debug) printf("updating color map...\n");

  xtvcolorld(disp->r,disp->g,disp->b,256);

  if (strcasecmp(img->file,"NONE")==0)
    updatename(img->fullname,1);
  else
    updatename(img->file,1);
  
  updatename(img->object,2);
  
  sprintf(reply,"Displayed image %s with limits z1=%.3f z2=%.3f",
	  fname,disp->z1,disp->z2);
  
  return 0;

}

//---------------------------------------------------------------------------
//
// File Transfer Functions
//

/*!
  \brief Test filename to see if the file exists and is a regular file

  \param fname string with the filename to test
  \return 1 if fname exists and a regular file, 0 if does not exist, 
  -1 if bad errors occurred, otherwise if it exists but not a regular file 
  (e.g., a directory) it returns -type, where type is one
  of the S_IFxxx codes in sys/stat.h

  Uses stat() to test the state of the named file.

  \sa isDir()
*/

int
isFile(char *fname)
{
  struct stat statbuf;
  int itype;

  // Try to stat fname, if it doesn't exist, return 0
  // Other errors are bad, return -1

  if (stat(fname,&statbuf)<0) {
    switch(errno) {
    case ENOENT:
      return 0;
      break;
    default:
      return -1;
      break;
    }
  }

  // Exists, now check type.  If not a regular file, return the type
  // code as -(itype)

  itype = (statbuf.st_mode & S_IFMT);

  if (itype == S_IFREG)
    return 1;
  else
    return -itype;

}

/*!
  \brief Test a directory path to see if it exists and is a directory

  \param path string with the directory path to test
  \return 1 if path exists and is a directory, 0 if does not exist, 
  -1 if bad errors occurred, otherwise if it exists but is not a 
  directory (e.g., a file) it returns -type, where type is one
  of the S_IFxxx codes in sys/stat.h

  Uses stat() to test the state of the named directory path.

  \sa isFile()
*/

int
isDir(char *path)
{
  struct stat statbuf;
  int itype;

  // Try to stat path, if it doesn't exist, return 0
  // Other errors are bad, return -1

  if (stat(path,&statbuf)<0) {
    switch(errno) {
    case ENOENT:
      return 0;
      break;
    default:
      return -1;
      break;
    }
  }

  // Exists, now check type.  If not a directory, return the
  // type code as -(itype)

  itype = (statbuf.st_mode & S_IFMT);

  if (itype == S_IFDIR)
    return 1;
  else
    return -itype;

}

/*!
  \brief Initialize an #xfer_params data structure

  \param trans pointer to an #xfer_params data structure

  Fills the data members of trans with suitable default
  values.

  \sa XferInfo()
*/

void
InitXferPars(xfer_t *trans)
{
  trans->doTransfer = 0;   // disable transfer by default (safety)
  trans->clobber = 0;      // default is to disallow overwrite (noclobber)
  trans->marksrc = 1;      // default is to mark processed images (mark)
  trans->backimg = 1;      // default is to backup old destination image if transfer would clobber (backup)
  strcpy(trans->imgPath,""); // default paths and files are null
  strcpy(trans->srcPath,"");
  strcpy(trans->file,"");

  trans->bufsize = 1024;     // default buffer size
}

/*!
  \brief Print contents of an #xfer_params data structure to stdout
  
  \param trans pointer to an #xfer_params data structure

  Prints the contents of the #xfer_params data structure describing
  the image transfer parameters to stdout.  Designed primarily as an
  engineering function.

  \sa InitXferPars()
*/

void
XferInfo(xfer_t *trans)
{
  printf("Image Transfer Parameters:\n");
  printf("  Image Transfer %s\n",
	 (trans->doTransfer) ? "Enabled" : "Disabled");
  printf("  Destination Image Overwrite (clobber) %s\n",
	 (trans->clobber) ? "Enabled" : "Disabled");
  printf("  Destination Image Backup if Transfer would Clobber %s\n",
	 (trans->backimg) ? "Enabled" : "Disabled");
  printf("  Source Image Process Marking %s\n",
	 (trans->marksrc) ? "Enabled" : "Disabled");
  if (strlen(trans->imgPath)>0)
    printf("  Image Destination Path: %s\n",trans->imgPath);
  else
    printf("  Image Destination Path: NONE\n");
  if (strlen(trans->srcPath)>0)
    printf("  Image Source Path: %s\n",trans->srcPath);
  else
    printf("  Image Source Path: NONE\n");
  if (strlen(trans->file)>0)
    printf("  Last File Transferred: %s\n",trans->file);
  printf("  Transfer Buffer: %d bytes\n",trans->bufsize);

}

/*!
  \brief Transfer an image from the source to destination directory

  \param trans pointer to an #xfer_params data structure
  \param fname name of the file to transfer (no path)
  \param reply string with any transfer reply text

  \return 0 if successful, -1 if an error.  Error or success
  messages are in the reply string.

  Transfers a file (byte-for-byte copy) from the source path to the
  destination path specified by #xfer_params::srcPath and
  #xfer_params::imgPath.  If #xfer_params::clobber=1, it will allow
  the transfer to overwrite any existing files on
  #xfer_params::imgPath.

  If #xfer_params::clobber=0, then overwrite is not permitted, and the
  transfer attempt will abort with errors unless
  #xfer_params::backimg=1, at which point a backup of the existing
  image is created (renaming in-place with the .bak extension appended
  to the name) before transferring.

  On successful tranfer, the name of the file will be placed in the
  #xfer_params::file string and the function will return 0 and a
  success message in reply.

  Also on successful transfer, if the #xfer_params::marksrc flag is
  true, the name of the source file will be change in-place to append
  the .proc extension to the file to say "I have been processed".

  On errors, the function returns -1 and any error messages generated
  are in the reply string.

*/

int
TransferImage(xfer_t *trans, char *fname, char *reply)
{
  char srcfile[256];  // full source filename
  char destfile[256]; // full destination filename
  char markfile[256];  // srcfile marked with .proc if trans->marksrc true
  char backfile[256];  // backup file name if trans->backimg true
  int srcFD;  // source file descriptor
  int destFD; // destination file descriptor
  char buf[XFERBUF];  // transfer buffer 
  int n;      // number of bytes transferred
  double t1, t2, dt;
  int didBack;

  // Basic initializations

  didBack = 0;  // no backup required

  // First verify that transfer is enabled.

  if (!trans->doTransfer) {
    strcpy(reply,"File Transfer not enabled");
    return -1;
  }

  // Have we been given a file to transfer?

  if (strlen(fname)==0) {
    strcpy(reply,"No file given for the transfer");
    return -1;
  }

  // Build the full input filename and test it exists

  memset(srcfile,0,sizeof(srcfile));
  sprintf(srcfile,"%s/%s",trans->srcPath,fname);

  if (isFile(srcfile)<1) {
    sprintf(reply,"Source file '%s' does not exist",srcfile);
    return -1;
  }

  // If trans->marksrc set, fill markfile with srcfile with
  // .proc appended.  We don't care if srcfile.proc exists,
  // the current rule is to clobber .proc files

  if (trans->marksrc) {
    memset(markfile,0,sizeof(markfile));
    sprintf(markfile,"%s.proc",srcfile);
  }

  // Build the full output file, and a backup filename if
  // trans->backimg is true.

  memset(destfile,0,sizeof(destfile));
  sprintf(destfile,"%s/%s",trans->imgPath,fname);

  if (trans->backimg) {
    memset(backfile,0,sizeof(backfile));
    sprintf(backfile,"%s.bak",destfile);
  }

  // If the destination file exists, take appropriate action
  //   if trans->backimg true, attempt to make a backup copy, then
  //      proceed with the transfer.  Abort on any errors creating
  //      the backup copy.  Note the backup copy *will* clobber:
  //      the user only gets one chance...
  //   if trans->backimg false, signal and error and abort attempt

  if (isFile(destfile)>0 && (!trans->clobber)) {
    if (trans->backimg) {
      if (rename(destfile,backfile)<0) {  // bad, can't backup, abort!
	sprintf(reply,"Transfer would overwrite '%s' and backup creation failed - %s",
		destfile,strerror(errno));
	return -1;
      }
      didBack = 1;
    }
    else {
      sprintf(reply,"Destination file '%s' exists - transfer would overwrite",destfile);
      return -1;
    }
  }

  // We've passed our basic tests, try opening files

  srcFD = open(srcfile,O_RDONLY);
  if (srcFD<0) {
    sprintf(reply,"Cannot open source file %s - %s\n",
	    srcfile,strerror(errno));
    return -1;
  }

  destFD = open(destfile,O_WRONLY|O_CREAT,0644);
  if (destFD<0) {
    sprintf(reply,"Cannot open destination file %s - %s\n",
	    destfile,strerror(errno));
    close(srcFD);
    return -1;
  }

  t1 = SysTimestamp();
  while ((n=read(srcFD,buf,XFERBUF))>0) 
    write(destFD,buf,n);
  t2 = SysTimestamp();
  dt = t2 - t1;

  // close the files

  close(srcFD);
  close(destFD);

  // save the name of the file transferred

  strcpy(trans->file,fname);

  // If we are marking the transferred source file with .proc, do it
  // now.  We use rename() from stdio.h, and allow clobber but trap
  // any badness as a warning.  On errors, rename() will retain the
  // original.

  if (trans->marksrc) {
    if (rename(srcfile,markfile)<0) {
      sprintf(reply,"Wrote LASTFILE=%s XferTime=%.3f sec, WARNING source file %s not marked - %s",
	      destfile,dt,srcfile,strerror(errno));
      return 0;
    }
  }

  if (didBack)
    sprintf(reply,"Wrote LASTFILE=%s BackUpFile=%s XferTime=%.3f sec",destfile,backfile,dt);
  else
    sprintf(reply,"Wrote LASTFILE=%s XferTime=%.3f sec",destfile,dt);

  return 0;
}

//---------------------------------------------------------------------------
//
// Post-Processing Functions
//

/*!
  \brief Initialize a #proc_param data structure

  \param proc pointer to a #proc_param data structure

  Initializes the post-processing data structure
  by zeroing the processor count and releasing all
  assoicated memory.

*/

void
InitPostProc(proc_t *proc)
{
  int i;

  proc->Nproc = 0;

  for (i=0;i<MAX_PROCS;i++) {
    if (proc->Cmd[i] != NULL) 
      free(proc->Cmd[i]);
    proc->Cmd[i] = NULL;
    proc->doProc[i] = 0;
  }
}

/*!
  \brief Print contents of an #proc_params data structure to stdout
  
  \param proc pointer to an #proc_params data structure

  Prints the contents of the #proc_params data structure describing
  the various external post-processing commands that are currently
  loaded to stdout.  Designed primarily as an engineering function.

  \sa InitPostProc()
*/

void
PostProcInfo(proc_t *proc)
{
  int i;

  printf("Image Post-Processing Parameters:\n");
  if (proc->Nproc >0) {
    printf("  %d Number of PostProcessing Commands\n",
	   proc->Nproc);
  }
  else {
    printf("  No PostProcessing Commands\n");
    return;
  }

  for (i=0;i<proc->Nproc;i++)
    printf("     Command %d: %s [%s]\n",i+1,proc->Cmd[i],
	   (proc->doProc[i] ? "Enabled" : "Disabled"));

}

/*!
  \brief Execute a PostProcessing Command

  \param proc pointer to a #proc_params data structure
  \param iproc index of the command to process (1..#MAX_PROCS)
  \param fname filename to process
  \param reply string with any postprocessing reply text

  \return 0 on success, -1 on errors.  Success or error text in reply

  Executes the postprocessing command indexed by iproc on file fname
  using a popen/pclose pair

*/

int
PostProcImg(proc_t *proc, int iproc, char *fname, char *reply)
{
  int i;
  FILE *cmdpipe;
  char cmdstr[128];

  // Is the requested post-processing command in range?

  if (iproc < 1 || iproc > MAX_PROCS) {
    sprintf(reply,"Invalid Post-Processing command %d - must be 1..%d",
	    iproc,MAX_PROCS);
    return -1;
  }

  // Is the post-processing command actually enabled?  Do it

  if (proc->doProc[iproc-1]) {
    memset(cmdstr,0,sizeof(cmdstr));
    sprintf(cmdstr,proc->Cmd[iproc-1],fname);
    cmdpipe = popen(cmdstr,"r");
    if (cmdpipe !=0) {
      pclose(cmdpipe);
      sprintf(reply,"Executed '%s'",cmdstr);
      return 0;
    }
    else {
      sprintf(reply,"Command '%s' generated errors",cmdstr);
      return -1;
    }
  }
  sprintf(reply,"Command %d (%s) not enabled",iproc,
	  proc->Cmd[iproc-1]);
  return -1;

}


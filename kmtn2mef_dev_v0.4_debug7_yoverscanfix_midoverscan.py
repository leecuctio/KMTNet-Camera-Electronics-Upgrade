import sys, os, math
import numpy as np
from astropy.io import fits
from astropy.io.fits import getval
from astropy.io.fits import update
from astropy import units as u
from astropy.coordinates import SkyCoord
import getopt
import warnings
import pandas as pd

warnings.filterwarnings('ignore',category=UserWarning, append=True)
warnings.filterwarnings('ignore',category=RuntimeWarning, append=True)

verName = "kmtn2mef_64layer_v0.01"
verDate = "2025-07-22"

verbose = False
clobber = False
convert = False   # if True, convert to floats
outDir = "./"     # output MEF files are written to ./ by default

primaryD = 1.600 # primary mirror diameter in meters
telFR = 3.22     # telescope focal ratio
telScale = 40.04 # pixel image in arcsec/mm

ccdCols = 9216 # unbinned active CCD column size in pixels
ccdRows = 9232 # unbinned active CCD row size in pixels
pixSize = 10.0 # pixel size in microns
pixScale = telScale*(pixSize/1000.)  # pixel scale in arcsec/pixel

gapCols = 460
gapRows = 933

detC1 = {'K':ccdCols+gapCols+1, 'M':1, 'T':ccdCols+gapCols+1, 'N':1}
detR1 = {'K':ccdRows+gapRows+1, 'M':ccdRows+gapRows+1, 'T':1, 'N':1}

CRPIX1 = {'K':-(gapCols//2), 'M':ccdCols+(gapCols//2), 'T':-(gapCols//2), 'N':ccdCols+(gapCols//2)}
CRPIX2 = {'K':-(gapRows//2), 'M':-(gapRows//2), 'T':ccdRows+(gapRows//2), 'N':ccdRows+(gapRows//2)}
print('DEBUG: CRPIX1 =', CRPIX1)
print('DEBUG: CRPIX2 =', CRPIX2)

CROTA1 = {'K':0.0,'M':0.0,'T':0.0,'N':0.0}
CROTA2 = {'K':0.0,'M':0.0,'T':0.0,'N':0.0}

CDELT1 = -pixScale/3600.0  # x transform scale factor in deg/pixel (- = E left)
CDELT2 =  pixScale/3600.0  # y transform scale factor in deg/pixel (+ = N up)

CD1_1 = {'K':CDELT1, 'M':CDELT1, 'N':CDELT1, 'T':CDELT1}
CD1_2 = {'K':0.0,'M':0.0,'T':0.0,'N':0.0}
CD2_1 = {'K':0.0,'M':0.0,'T':0.0,'N':0.0}
CD2_2 = {'K':CDELT2, 'M':CDELT2, 'N':CDELT2, 'T':CDELT2}

ccdList = ['M','K','N','T']
flipXY  = {'K':False, 'M':False, 'N':False, 'T':False}

haveSEF = {'MK':False, 'NT':False}
numSEF = 0
requireAll = False   # do not require all 2 images by default

def printUsage(help=False):
    print ("\nUsage: kmtn2mef rawFile [options]")
    print ("\nwhere:")
    print ("   rawFile = one raw KMTNx.ccyymmdd.######.fits filename, x={k,m,n, or t}")
    print ("             It create the names of all 4 files from this one.")
    print ("\nCreates kmt?.ccyymmdd.######.fits, a 32-extension MEF file,")
    print ("  where ? is c for CTIO, s for SAAO, and a for SSO.")
    print ("The MEF file is written to the current working directory (but see -o)")
    print ("\noptions:")
    print ("   -o outdir = write the MEF file in outdir [default: create in place]")
    print ("   -f = force overwrite of an existing MEF file [default: no overwrite]")
    print ("   -a = require all 4 raw images [default: allow missing images]")
    print ("   -c = convert raw datatype to floating point [default: no conversion]")
    print ("   -h = print more detailed help and exit")
    print ("   -v = verbose output for debugging [default: quiet]")
    print ("   -V = print version info and quit")
    print ("")
    if help:
        print ("Detailed Help:")
        print ("\nIf no directory path is given as part of the input file name, all of")
        print ("the raw FITS files must be in the current working directory.  If a")
        print ("directory path *is* given (e.g., /data/KMTNk.20150205.001234.fits),")
        print ("then all raw images must be in that directory.")
        print ("\nBy default, the output MEF file is created in the current working")
        print ("directory.  You can direct the output to another directory with the")
        print ("-o option (e.g., -o /archive/data).  Note that the target directory")
        print ("must already exist and be writable (this program will not create it).")
        print ("\nIf a raw image is missing, it fills its extension data units")
        print ("with zeros and notes its absence by setting the K/M/T/NFILE='None'")
        print ("keyword in the primary header.  It also sets the NUMFILES keyword to")
        print ("the number of raw files present (<4 means one or more were missing).")
        print ("Note, however, that because the K image contains the master header")
        print ("with critical timing data, if K is missing no MEF is created.")
        print ("\nYou can require that all four images must exist for MEF creation by")
        print ("using the -a/--all option.")
        print ("\nBy default, the MEF file created preserves the data type of the")
        print ("original raw images.  The -c option allows you to convert raw integer")
        print ("data to 32-bit floating point (BITPIX=-32) data, but note that this")
        print ("will double the size of the output MEF file.")
        print ("")

try:
    opts, files = getopt.getopt(sys.argv[1:], 'Vvfao:h',
                               ['verbose','version','force','all','output=','help'])

except getopt.GetoptError:
    print(f"Usage: kmtn2mef.py [-f] [-o output_dir] KMTN.YYYYMMDD.######.MK.fits")
    sys.exit(1)

if len(opts)==0 and len(files)==0:
    printUsage()
    sys.exit(1)

for opt, arg in opts:
    if opt in ( '-V','--version'):
        print(f"{verName} ({verDate})")
        sys.exit(0)

    elif opt in ('-v', '--verbose'):
        verbose = True

    elif opt in ('-f', '--force'):
        clobber = True
        print('DEBUG: clobber =', clobber)


    elif opt in ('-a','--all'):
        requireAll = True

    elif opt in ('-o', '--outdir'):
        outDir = arg

    elif opt in ('-h','--help'):
        printUsage(help=True)
        sys.exit(0)

numFiles = len(files)

if numFiles == 1:
    kmtFile = files[0]
else:
    printUsage()
    sys.exit(1)

baseName = os.path.splitext(kmtFile)[0]
baseBits = baseName.split('.')
inputDir = os.path.dirname(kmtFile)
fileRoot = "%s.%s" % (baseBits[1],baseBits[2])



if "MK.fits" in kmtFile:
    mk_File = kmtFile
    print(f"MK file detected: {mk_File}")
    nt_File = mk_File.replace("MK.fits", "NT.fits")

try:
    observat = getval(mk_File,'observat')
except:
    print("** ERROR: OBSERVAT keyword not found in (mk_File)")
    print("          kmtn2mef aborting with errors")
    sys.exit(1)


# Build the output MEF Filename, including the output directory path

if observat=='CTIO':
    mefFile = os.path.join(outDir,"kmtc.%s.fits" % (fileRoot))
elif observat=='SAAO':
    mefFile = os.path.join(outDir,"kmts.%s.fits" % (fileRoot))
elif observat=='SSO':
    mefFile = os.path.join(outDir,"kmta.%s.fits" % (fileRoot))
else:
    print("** ERROR: Unrecognized OBSERVAT value {observat}")
    print("          kmtn2mef aborting with errors")
    sys.exit(1)

print (f"{observat}")

# Does the MEF file already exist?  If it does, and we have not
# explicitly set -f/--force, complain with a suggestion to use
# -f/--force to override the no-clobber rule.

if os.path.isfile(mefFile):
    if clobber:
        if verbose:
            print("**WARNING: Overwriting existing MEF file %s" % (mefFile))
        os.remove(mefFile)
    else:
        print("**ERROR: Output MEF file %s already exists." % (mefFile))
        print("         Use -f or --force to overwrite it.")
        print("kmtn2mef aborting.")
        sys.exit(1)

numErr = 0
hasMK = False
FILELIST = [ 'MK', 'NT' ]
for TAG in FILELIST:
    sefFile = os.path.join(inputDir,"KMTN.%s.%s.fits" % (fileRoot,TAG))
    if not os.path.isfile(sefFile):
        numErr += 1
    else:
        haveSEF[TAG] = True
        numSEF += 1
        if TAG == 'MK':
            hasMK = True

if not hasMK:
    print("** ERROR: The master MK image KMTN.%s.MK.fits is missing" % (fileRoot))
    print("   Cannot assemble the MEF if the master header is missing.")
    print("   kmtn2mef aborting with errors.")
    sys.exit(1)

if numErr > 0:
    if requireAll:
        print("** ERROR: %d of %d raw KMTN.%s.x.fits files missing" % (numErr,len(FILELIST),fileRoot))
        print("   Missing File(s):")
        for TAG in FILELIST:
            if not haveSEF[TAG]:
                print (f"      KMTN.%s.%s.fits" % (fileRoot,TAG))
        print (f"   Cannot assemble the MEF file, kmtn2mef aborting with errors.")
        sys.exit(1)
    else:
        print("** ERROR: %d of %d raw KMTN.%s.x.fits files missing" % (numErr,len(FILELIST),fileRoot))

        print("   Missing File(s):")
        for TAG in FILELIST:
            if not haveSEF[TAG]:
                print("      KMTN.%s.%s.fits" % (fileRoot,TAG))
        print("   A zero data placeholder will be used instead.")


if not hasMK:
    masterFile = os.path.join(inputDir,"KMTN.%s.NT.fits" % (fileRoot))
else:
    masterFile = os.path.join(inputDir,"KMTN.%s.MK.fits" % (fileRoot))

filtername = getval(masterFile,'filter')
object = getval(masterFile,'object')
projid = getval(masterFile,'projid')
imagetyp = getval(masterFile,'imagetyp')
obstype = getval(masterFile,'obstype')
tshopen = getval(masterFile,'tshopen')
dateobs = getval(masterFile,'date-obs')
#alt = getval(masterFile,'alt')
az = getval(masterFile,'az')
secz = getval(masterFile,'secz')
ha = getval(masterFile,'ha')
st = getval(masterFile,'st')
#ra = getval(masterFile,'ra')
#dec = getval(masterFile,'dec')

print(" %s %s %s %s %s %s %s %s %s %s %s" % (filtername, object, projid, imagetyp, obstype, tshopen, dateobs, az, secz, ha, st))

bitpix = getval(masterFile,'bitpix')
if bitpix==16:
    bzero = getval(masterFile,'bzero')
    bscale = getval(masterFile,'bscale')
elif bitpix==32:
    bzero = getval(masterFile,'bzero')
    bscale = getval(masterFile,'bscale')
else:
    #convert = True  # not an integer, so floating pass-thru
    convert = False # not an integer, so floating pass-thru

if verbose:
    if bitpix > 0:
        print("Images are bitpix=%d bzero=%d bscale=%d" % (bitpix,bzero,bscale))
        if convert:
            print("Will convert to bitpix=-32 on output")
        else:
            print("Will preserve bitpix=%d scaling on output" % (bitpix))
    else:
        print("Images are floating data with bitpix=%d" % (bitpix))

inFITS = fits.open(masterFile)
inHdr = inFITS[0].header

if 'NAMPS' in inHdr:
    numAmps = inHdr['NAMPS']
else:
    numAmps = 16

if 'OVERSCNX' in inHdr:
    biasCols = inHdr['OVERSCNX']
else:
    biasCols = 48

if 'PRESCANX' in inHdr:
    preCols = inHdr['PRESCANX']
else:
    preCols = 0

naxis1 = inHdr['naxis1']
print("NAXIS1 = %s " % (naxis1))

dataCols = naxis1 - numAmps*(preCols+biasCols)
naxis2 = inHdr['naxis2']

# NOTE: Some newer raw images include extra overscan rows in Y.
#       Example: naxis2=9400 (raw) while the active science area is still ccdRows=9232.
#       We *ignore* any extra Y rows (overscan) when building the MEF.
rawRows       = naxis2
rawHalfRows   = rawRows // 2
activeHalfRows = ccdRows // 2   # active rows per amp (e.g., 4616)
if rawRows < 2*activeHalfRows:
    # Fallback for unexpected headers
    activeHalfRows = rawHalfRows
# Extra Y rows are assumed to be a *middle* overscan block between lower and upper halves.
midOverRows   = max(0, rawRows - 2*activeHalfRows)

dataRows   = activeHalfRows
stripeCols = int(dataCols/numAmps)
stripeRows = dataRows

print(f"DEBUG: NAXIS2(raw)={rawRows}  rawHalfRows={rawHalfRows}  activeHalfRows={activeHalfRows}  midOverRows(ignored)={midOverRows}") 
print("dataCols   = naxis1( %s ) - nmAmps( %s ) * ( preCols(%s) + biasCols(%s)) " % (naxis1,numAmps,preCols,biasCols))
print("dataCols   = %s " % (dataCols))
print("stripeCols = %s " % (stripeCols))
print("stripeRows = %s " % (dataRows))

if 'ALT' in inHdr:
   numALT = inHdr['ALT']
else:
   numALT = 0

print(" %s " % (naxis1))
print(" %s " % (naxis2))
print(" %s " % (numALT))

if 'RA' in inHdr:
    RA = inHdr['RA']
    if RA == "                       / Telescope RA":
        RA = "00:00:00.00"
        ra = "00:00:00.00"
        inHdr.remove('RA')
        inHdr['RA'] = ( '%s' % RA, 'Telescope RA')
    else:
        RA = inHdr['RA']
else:
    RA = "00:00:00.00"

if 'DEC' in inHdr:
    Dec = inHdr['DEC']
    if Dec == "                       / Telescope DEC":
        Dec = "+00:00:00.0"
        dec = "+00:00:00.0"
        inHdr.remove('DEC')
        inHdr['DEC'] = ( '%s' % Dec, 'Telescope DEC')
    else:
        Dec = inHdr['DEC']
        dec = inHdr['DEC']
else:
    Dec = "+00:00:00.0"
    dec = "+00:00:00.0"

print(" RA  : %s " % (RA))
print(" DEC : %s " % (Dec))

coord = SkyCoord(RA, Dec, frame='icrs', unit=(u.hourangle, u.deg))
CRVAL1 = coord.ra.degree
CRVAL2 = coord.dec.degree


print(" %s " % (numAmps))

for i in range(numAmps):
    preKey = 'PRESCAN%d' % (i+1)
    dataKey = 'DATA%d' % (i+1)
    biasKey = 'BIAS%d' % (i+1)
    if preKey in inHdr:
        del inHdr[preKey]
    if dataKey in inHdr:
        del inHdr[dataKey]
    if biasKey in inHdr:
        del inHdr[biasKey]
    if 'DETID' in inHdr:
        del inHdr['DETID']


if 'FILENAME' in inHdr:
    inHdr['FILENAME'] = (mefFile,'MEF Filename')

if 'CREATOR' in inHdr:
    inHdr['CREATOR'] = ('%s %s' % (verName,verDate),'MEF File Creation Program')


detCols = gapCols + 2*ccdCols
print('DEBUG: detCols =', detCols)
detRows = gapRows + 2*ccdRows
print('DEBUG: detRows =', detRows)

inHdr.set('DETSIZE',
          '[%d:%d,%d:%d]' % (1, detCols, 1, detRows),
          'KMNT Mosaic size in Pixels')

print(type(inHdr['DETSIZE']))
print(f"DETSIZE = {inHdr['DETSIZE']}")

date = dateobs[0:10]
print('DEBUG: date =', date)

if obstype in "BIAS" and object in "bias"     \
   or obstype in "DARK" and object in "dark"  \
   or obstype in "DARK" and object in "begin" \
   or obstype in "DARK" and object in "end":
   ut = "----------------------"
   print('DEBUG: ut =', ut)
else:
   ut = date + "T" + inHdr['TSHOPEN']
   print('DEBUG: ut =', ut)

inHdr['UT'] = (ut,'Master IC reports shutter open time')


print('numSEF = ', numSEF)

inHdr['NUMFILES'] = (numSEF,'Number of Single-CCD FITS files')
for TAG in ['MK','NT']:
    print("=============================================================== %s " % (TAG) )
    sefKey = "%sCCDFILE" % (TAG)
    print('DEBUG: sefKey =',sefKey)
    if haveSEF[TAG]:
        sefFile = os.path.join(inputDir,"KMTN.%s.%s.fits" % (fileRoot,TAG))
        print('DEBUG: sefFile =', sefFile)
        sefComment = "%s CCD FITS File" % (TAG)
        print('DEBUG: sefComment =', sefComment)
    else:
        sefFile = 'None'
        print('DEBUG: sefFile =', sefFile)
        sefComment = "%s CCD FITS File" % (TAG)
        print('DEBUG: sefComment =', sefComment)
    inHdr[sefKey] = (sefFile,sefComment)


print(" ")
print("+-------------------------------------------------------------+")
inHdr['COLGAP'] = (gapCols,'Horizontal inter-CCD gap in pixels')
inHdr['ROWGAP'] = (gapRows,'Vertical inter-CCD gap in pixels')

primary = fits.PrimaryHDU(header=inHdr)
print('DEBUG: primary =', primary)
newHDU = fits.HDUList([primary])
print('DEBUG: newHDU =', newHDU)
newHDU.writeto(mefFile)

# All done with the masterFile, close it

inFITS.close()

print(" ")

for TAG in ['MK','NT']:
    print("=============================================================== %s " % (TAG))
    sefFile = os.path.join(inputDir,"KMTN.%s.%s.fits" % (fileRoot,TAG))
    print('DEBUG: sefFile =', sefFile)

    if verbose:
        print("Processing image %s..." % (sefFile))


    if TAG == "MK":
        ccdLIST = ['M', 'K']
    elif TAG == "NT":
        ccdLIST = ['N', 'T']
    else:
        raise ValueError(f"Unknown TAG value: {TAG}")


    with fits.open(sefFile) as hdu:
        inData = hdu[0].data

    print("- - - - - - - - - - - - - - - - - - - - - - - - - << %s START >> " % (TAG))
    for ccd in ccdLIST:
       if ccd in ['M', 'N']:
           position = 'LEFT'
           detID    = ccd
       elif ccd in ['K','T']:
           position = 'RIGHT'
           detID    = ccd
       else:
           raise ValueError(f"Unknown CCD identifier: {ccd}")

       print('DEBUG: ccd , position = ', ccd,  position)


       print(f"{TAG} {ccd} {position}")
       print('DEBUG: detID =', detID)

       doFlip = flipXY[detID]
       print('DEBUG: doFlip =', doFlip)
       detC0 = detC1[detID]
       print('DEBUG: detC0 =', detC0)
       detR0 = detR1[detID]
       print('DEBUG: detR0 =', detR0)

       if verbose:
           if doFlip:
               print("   Flipping X and Y")

       stripe = np.zeros(( int(stripeRows), int(preCols + stripeCols + biasCols)), dtype=np.float32)

       print('DEBUG: stripe shape =', stripe.shape)
       print('DEBUG: stripe dtype =', stripe.dtype)
       print('DEBUG: stripe =', stripe)

       if ccd in ['M','K','N','T']:

           AMP_WIDTH        = 1152
           AMP_HEIGHT       = 4616
           BIAS_WIDTH       = 48
           GAP_WIDTH        = 49
           NUM_AMPS_PER_ROW = 8

           print('DEBUG: CCD  =', ccd)

           ## CCDSEC/AMPSEC ##
           def get_ccdsec_x1(amp):
               return ( amp - 1 ) % 8 * AMP_WIDTH + 1
           def get_ccdsec_x2(amp):
               return ((amp - 1 ) % 8 + 1 ) * AMP_WIDTH
           #def get_ccdsec_y1(amp):
           #    return 4617 if amp <= 8 else 1

           #def get_ccdsec_y2(amp):
           #    return 9232 if amp <= 8 else 4616
           def get_ccdsec_y1(amp):
               return 1
           def get_ccdsec_y2(amp):
               return stripeRows

           ## DATASEC ##
           def get_datasec_x1(amp):
               return 1 if (amp - 1) % 8 < 4 else 49

           def get_datasec_x2(amp):
               return 1152 if (amp - 1) % 8 < 4 else 1200
          
           #def get_datasec_y1(amp):
           #    return 4617 if amp <= 8 else 1
          
           #def get_datasec_y2(amp):
           #    return 9232 if amp <= 8 else 4616
           def get_datasec_y1(amp):
               return 1
           def get_datasec_y2(amp):
               return stripeRows

           ## PRESEC ##
           def get_presec_x1(amp):
               return 0
          
           def get_presec_x2(amp):
               return 0
          
           #def get_presec_y1(amp):
           #    return 4617 if amp <= 8 else 1
          
           #def get_presec_y2(amp):
           #    return 9232 if amp <= 8 else 4616
           def get_presec_y1(amp):
               return 1
           def get_presec_y2(amp):
               return stripeRows

           ## BIASSEC ##
           def get_biassec_x1(amp):
               return 1153 if amp in range(1, 5) or amp in range(9, 13) else 1

           def get_biassec_x2(amp):
               return 1200 if amp in range(1, 5) or amp in range(9, 13) else 48

           #def get_biassec_y1(amp):
           #    return 4617 if amp <= 8 else 1

           #def get_biassec_y2(amp):
           #    return 9232 if amp <= 8 else 4616
           def get_biassec_y1(amp):
               return 1
           def get_biassec_y2(amp):
               return stripeRows

           ## TRIMSEC ##
           def get_trimsec_x1(amp):
               return 1 if (1 <= amp <= 4 or 9 <= amp <= 12) else 49
          
           def get_trimsec_x2(amp):
               return 1152 if (1 <= amp <= 4 or 9 <= amp <= 12) else 1200
          
           #def get_trimsec_y1(amp):
           #    return 4617 if amp <= 8 else 1
           
           #def get_trimsec_y2(amp):
           #    return 9232 if amp <= 8 else 4616
           def get_trimsec_y1(amp):
               return 1
           def get_trimsec_y2(amp):
               return stripeRows

           ## DETSEC ##
           def get_detsec_x1(chip, amp):
               if chip in ["M", "N"]:  # Left chips
                   if 1 <= amp <= 8:
                       return (amp - 1) * 1152 + 1
                   elif 9 <= amp <= 16:
                       return (amp - 9) * 1152 + 1
               elif chip in ["K", "T"]:  # Right chips (offset = 9676)
                   if 1 <= amp <= 8:
                       return (amp - 1) * 1152 + 9677
                   elif 9 <= amp <= 16:
                       return (amp - 9) * 1152 + 9677
               else:
                   raise ValueError("Invalid chip")
          
           def get_detsec_x2(chip, amp):
               return get_detsec_x1(chip, amp) + 1151
          
           def get_detsec_y1(chip, amp):
               if chip in ["M", "K"]:  # Upper chips
                   if 1 <= amp <= 8:
                       return 14782
                   elif 9 <= amp <= 16:
                       return 10166
               elif chip in ["N", "T"]:  # Lower chips
                   if 1 <= amp <= 8:
                       return 4617
                   elif 9 <= amp <= 16:
                       return 1
               else:
                   raise ValueError("Invalid chip")
          
           def get_detsec_y2(chip, amp):
               if chip in ["M", "K"]:  # Upper chips
                   if 1 <= amp <= 8:
                       return 19397
                   elif 9 <= amp <= 16:
                       return 14781
               elif chip in ["N", "T"]:  # Lower chips
                   if 1 <= amp <= 8:
                       return 9232
                   elif 9 <= amp <= 16:
                       return 4616
               else:
                   raise ValueError("Invalid chip")


           ## dataBeg, dataEnd, biasBeg, biasEnd
           def get_xdata_beg(chip, amp):
               if chip in ["M", "N"]:
                   base_offset = 0
               elif chip in ["K", "T"]:
                   base_offset = 9600
               else:
                   raise ValueError("Invalid chip")

               group = (amp - 1) % 8
               x_beg = group * 1200 + 1
               if amp in range(5, 9) or amp in range(13, 17):
                   x_beg += 48

               return x_beg + base_offset

           def get_xdata_end(chip, amp):
               if chip in ["M", "N"]:
                   base_offset = 0
               elif chip in ["K", "T"]:
                   base_offset = 9600
               else:
                   raise ValueError("Invalid chip")

               group = (amp - 1) % 8
               x_end = group * 1200 + 1152

               if amp in range(5, 9) or amp in range(13, 17):
                   x_end += 48

               return x_end + base_offset

           def get_xbias_beg(chip, amp):
               if chip in ["M", "N"]:
                   base_offset = 0
               elif chip in ["K", "T"]:
                   base_offset = 9600
               else:
                   raise ValueError("Invalid chip")
           
               group = (amp - 1) % 8
               data_x_beg = group * 1200 + 1
               data_x_end = data_x_beg + 1151
           
               if amp in range(5, 9) or amp in range(13, 17): 
                   bias_beg = data_x_beg
               else: 
                   bias_beg = data_x_end + 1
           
               return bias_beg + base_offset

           def get_xbias_end(chip, amp):
               if chip in ["M", "N"]:
                   base_offset = 0
               elif chip in ["K", "T"]:
                   base_offset = 9600
               else:
                   raise ValueError("Invalid chip")
           
               group = (amp - 1) % 8
               data_x_beg = group * 1200 + 1
               data_x_end = data_x_beg + 1151
           
               if amp in range(5, 9) or amp in range(13, 17): 
                   bias_end = data_x_beg + 47
               else: 
                   bias_end = data_x_end + 48
           
               return bias_end + base_offset

           # Y active rows in the raw image:
           #   - Newer raw frames can contain extra Y rows that are *middle* overscan between the
           #     lower and upper science halves.
           #   - Science rows are assumed to be:
           #       lower half : 1 .. activeHalfRows
           #       upper half : (rawRows-activeHalfRows+1) .. rawRows
           #     and the middle block is ignored.
           def get_yactive_beg(amp):
               return (rawRows - activeHalfRows + 1) if amp <= 8 else 1

           def get_yactive_end(amp):
               return rawRows if amp <= 8 else activeHalfRows

# Backward-compatible aliases (data and bias share the same Y range)
           def get_ydata_beg(amp):
               return get_yactive_beg(amp)

           def get_ydata_end(amp):
               return get_yactive_end(amp)

           def get_ybias_beg(amp):
               return get_yactive_beg(amp)

           def get_ybias_end(amp):
               return get_yactive_end(amp)

           ###
           def is_bias_right(amp):
               return amp in range(1, 5) or amp in range(9, 13)

           def get_stdataBeg(amp):
               return 1 if is_bias_right(amp) else 49

           def get_stdataEnd(amp):
               return 1152 if is_bias_right(amp) else 1200

           def get_stbiasBeg(amp):
               return 1153 if is_bias_right(amp) else 1

           def get_stbiasEnd(amp):
               return 1200 if is_bias_right(amp) else 48

           def get_y1(amp):
               return get_yactive_beg(amp)

           def get_y2(amp):
               return get_yactive_end(amp)

           for amp in range(1, 17):
               print("---------------------------------------------------------------")
               if ccd == 'M':
                  im = amp + 1 + 0 - 1
               elif ccd == 'K':
                  im = amp + 1 + 16 - 1
               elif ccd == 'N':
                  im = amp + 1 + 32 - 1
               elif ccd == 'T':
                  im = amp + 1 + 48 - 1

               if doFlip:
                   i = (numAmps-1) - amp
                   print('DEBUG: i =', i)
               else:
                   i = amp
                   print('DEBUG: i =', i)

               print(f"AMP : {amp}")
               print(f"im  : {im}")

               ccdsec  = f"[{get_ccdsec_x1(amp)}:{get_ccdsec_x2(amp)},{get_ccdsec_y1(amp)}:{get_ccdsec_y2(amp)}]"
               ampsec  = f"[{get_ccdsec_x1(amp)}:{get_ccdsec_x2(amp)},{get_ccdsec_y1(amp)}:{get_ccdsec_y2(amp)}]"
               datasec = f"[{get_datasec_x1(amp)}:{get_datasec_x2(amp)},{get_datasec_y1(amp)}:{get_datasec_y2(amp)}]"
               presec  = f"[{get_presec_x1(amp)}:{get_presec_x2(amp)},{get_presec_y1(amp)}:{get_presec_y2(amp)}]"
               biassec = f"[{get_biassec_x1(amp)}:{get_biassec_x2(amp)},{get_biassec_y1(amp)}:{get_biassec_y2(amp)}]"
               trimsec = f"[{get_trimsec_x1(amp)}:{get_trimsec_x2(amp)},{get_trimsec_y1(amp)}:{get_trimsec_y2(amp)}]"
               detsec  = f"[{get_detsec_x1(ccd,amp)}:{get_detsec_x2(ccd,amp)},{get_detsec_y1(ccd,amp)}:{get_detsec_y2(ccd,amp)}]"
               print(f"AMP {amp:2d}  ||  Layer_No {im:2d}  ||  {ccd}  ||  CCDSEC= {ccdsec:20}")
               print(f"AMP {amp:2d}  ||  Layer_No {im:2d}  ||  {ccd}  ||  AMPSEC= {ampsec:20}")
               print(f"AMP {amp:2d}  ||  Layer_No {im:2d}  ||  {ccd}  ||  DATASEC={datasec:20}")
               print(f"AMP {amp:2d}  ||  Layer_No {im:2d}  ||  {ccd}  ||  PRESEC={presec:20}")
               print(f"AMP {amp:2d}  ||  Layer_No {im:2d}  ||  {ccd}  ||  BIASSEC={biassec:20}")
               print(f"AMP {amp:2d}  ||  Layer_No {im:2d}  ||  {ccd}  ||  TRIMSEC={trimsec:20}")
               print(f"AMP {amp:2d}  ||  Layer_No {im:2d}  ||  {ccd}  ||  DETSEC= {detsec:20}")

               preBeg = 0
               print(f'DEBUG {ccd} amp{amp:2d} : preBeg   = {preBeg}')
               preEnd = 0
               print(f'DEBUG {ccd} amp{amp:2d} : preEnd   = {preEnd}')

               dataBeg = get_xdata_beg(ccd,amp) 
               print(f'DEBUG {ccd} amp{amp:2d} : dataBeg  = {dataBeg}')
               dataEnd = get_xdata_end(ccd,amp)
               print(f'DEBUG {ccd} amp{amp:2d} : dataEnd  = {dataEnd}')

               biasBeg = get_xbias_beg(ccd,amp)
               print(f'DEBUG {ccd} amp{amp:2d} : biasBeg  = {biasBeg}')
               biasEnd = get_xbias_end(ccd,amp)
               print(f"DEBUG {ccd} amp{amp:2d} : biasEnd  = {biasEnd}")

               crpix1_0 = get_ccdsec_x1(amp)
               print(f'DEBUG {ccd} amp{amp:2d} : CRPIX1_0 = {crpix1_0}')

               print("Processing Amplifier %s%02d:" % (ccd,amp))
               print("    Pre: %d to %d" % (preBeg,preEnd))
               print("   Data: %d to %d" % (dataBeg,dataEnd))
               print("   Bias: %d to %d" % (biasBeg,biasEnd))

               stPreBeg = 0
               print(f'DEBUG {ccd} amp{amp:2d} : stPreBeg =', stPreBeg)
               stPreEnd = 0
               print(f'DEBUG {ccd} amp{amp:2d} : stPreEnd =', stPreEnd)

               if  is_bias_right(amp):
                   stDataBeg = 1
                   print(f'DEBUG {ccd} amp{amp:2d} : stDataBeg =', stDataBeg)
                   stDataEnd = stripeCols
                   print(f'DEBUG {ccd} amp{amp:2d} : stDataEnd =', stDataEnd)
                   stBiasBeg = stDataEnd + 1
                   print(f'DEBUG {ccd} amp{amp:2d} : stBiasBeg =', stBiasBeg)
                   stBiasEnd = stDataEnd + biasCols
                   print(f'DEBUG {ccd} amp{amp:2d} : stBiasBeg =', stBiasBeg)
               else:
                   stBiasBeg = 1
                   print(f'DEBUG {ccd} amp{amp:2d} : stBiasBeg =', stBiasBeg)
                   stBiasEnd = biasCols
                   print(f'DEBUG {ccd} amp{amp:2d} : stBiasEnd =', stBiasEnd)
                   stDataBeg = stBiasEnd + 1
                   print(f'DEBUG {ccd} amp{amp:2d} : stDataBeg =', stDataBeg)
                   stDataEnd = stBiasEnd + stripeCols
                   print(f'DEBUG {ccd} amp{amp:2d} : stDataEnd =', stDataEnd)

                   print(f"{amp:2d}\t{get_stdataBeg(amp):4d}\t\t{get_stdataEnd(amp):4d}\t\t{get_stbiasBeg(amp):4d}\t\t{get_stbiasEnd(amp):4d}\t\t{get_y1(amp):4d}\t\t{get_y2(amp):4d}")


               if haveSEF[TAG]:
                   ydataBeg = get_ydata_beg(amp)
                   ydataEnd = get_ydata_end(amp)
                   preScan = inData[ydataBeg-1:ydataEnd, preBeg-1:preEnd]
                   print('DEBUG: preScan =', preScan)

                   print('DEBUG: =', dataBeg-1, dataEnd, ydataBeg-1, ydataEnd)
                   imgData = inData[ydataBeg-1:ydataEnd, dataBeg-1:dataEnd]
                   print(f"amp={amp} inData.shape={inData.shape} stripe.shape={stripe.shape}")
                   print(f"stripe[y1:y2, x1:x2].shape={stripe[int(ydataBeg)-1:int(ydataEnd), int(stDataBeg)-1:int(stDataEnd)].shape}")
                   print(f"imgData.shape={imgData.shape}")
                   print('DEBUG: imgData =', imgData)
                   imgBias = inData[ydataBeg-1:ydataEnd, biasBeg-1:biasEnd]
                   print('DEBUG: imgBias =', imgBias)


                   stripe[:, int(stPreBeg)-1:int(stPreEnd)] = preScan

                   if is_bias_right(amp):
#                   stripe[int(ydataBeg)-1:int(ydataEnd), int(stDataBeg)-1:int(stDataEnd)] = imgData
#                   stripe[int(ydataBeg)-1:int(ydataEnd), int(stBiasBeg)-1:int(stBiasEnd)] = imgBias
                       print('DEBUG: BIAS R || stripe {amp} =', amp)
                       stripe[:, int(stDataBeg)-1:int(stDataEnd)] = imgData
                       stripe[:, int(stBiasBeg)-1:int(stBiasEnd)] = imgBias
                       print(f"R stBias range = {stBiasBeg-1}:{stBiasEnd}")
                       print(f"R stData range = {stDataBeg-1}:{stDataEnd}")
                   else:
                       print('DEBUG: BIAS L || stripe {amp} =', amp)
                       stripe[:, int(stBiasBeg)-1:int(stBiasEnd)] = imgBias
                       stripe[:, int(stDataBeg)-1:int(stDataEnd)] = imgData
                       print(f"L stData range = {stDataBeg-1}:{stDataEnd}")
                       print(f"L stBias range = {stBiasBeg-1}:{stBiasEnd}")

                   print(f"preScan.shape: {preScan.shape}")
                   print(f"imgData.shape: {imgData.shape}")
                   print(f"imgBias.shape: {imgBias.shape}")
#                   print(f"stripe[:, a:b].shape: {stripe[:, int(stDataBeg)-1:int(stDataEnd)].shape}")

#               else:

#                   preScan = np.zeros((stripeRows,preCols),dtype=np.float32)
#                   print('DEBUG: preScan =', preScan)
#                   imgData = np.zeros((stripeRows,stripeCols),dtype=np.float32)
#                   print('DEBUG: imgData =', imgData)
#                   imgBias = np.zeros((stripeRows,biasCols),dtype=np.float32)
#                   print('DEBUG: imgBias =', imgBias)

#                   stripe[:,int(stPreBeg)-1:int(stPreEnd)] = preScan
#                   stripe[:,int(stDataBeg)-1:int(stDataEnd)] = imgData
#                   stripe[:,int(stBiasBeg)-1:int(stBiasEnd)] = imgBias
#                   stripe[y1:y2,int(stPreBeg)-1:int(stPreEnd)] = preScan
#                   stripe[y1:y2,int(stDataBeg)-1:int(stDataEnd)] = imgData
#                   stripe[y1:y2,int(stBiasBeg)-1:int(stBiasEnd)] = imgBias



               hdu = fits.ImageHDU(stripe)
               print('DEBUG: hdu =', hdu)
               hdr = fits.HDUList([hdu])[0].header
               print('DEBUG: hdr =', hdr)

               # The REALDATA keyword is T
               if haveSEF[TAG]:
                   hdr['REALDATA'] = (True,'Actual %s%02d stripe data' % (ccd,i+1))
               else:
                   hdr['REALDATA'] = (False,'Zero placeholder for missing %s data' % (ccd))

#               print(f"REALDATA = {hdr['REALDATA']}") 

               hdr['EXTNAME'] = ('%s%02d' % (ccd,i))
               hdr['CCDNAME'] = ('KMTNet CCD %s') % (ccd)

               print(f"EXTNAME  = {hdr['EXTNAME']}")
               print(f"CCDNAME  = {hdr['CCDNAME']}")

               hdr['AMPNAME'] = ('%s%02d' % (ccd,i))
               hdr['AMPNAME2'] = ('im%d' % (im))

               print(f"AMPNAME  = {hdr['AMPNAME']}")
               print(f"AMPNAME2 = {hdr['AMPNAME2']}")

               ### ---------------------------------- ###
#               hdr['GAIN'] = ('%3.1f' % (GAIN) )
#               hdr['RDNOISE'] = ('%3.1f' % (RDNOISE) )
               hdr['CCDSUM']  = ('1 1','On-Chip Binning Factors')

               print(f"{stripeCols}*{amp}+1,{stripeCols}*({amp}+1),1,{stripeRows}")

               hdr['CCDSEC']  = ('[%d:%d,%d:%d]' % (get_ccdsec_x1(amp),get_ccdsec_x2(amp),get_ccdsec_y1(amp),get_ccdsec_y2(amp)), 'CCD Data Section')
               print(f"CCDSEC   = {hdr['CCDSEC']}")


               #ampsec_x1 = 1
               #ampsec_x2 = stripeCols + biasCols
               #ampsec_y1 = get_ccdsec_y1(amp)
               #ampsec_y2 = get_ccdsec_y2(amp)
               ampsec_x1 = get_datasec_x1(amp)
               ampsec_x2 = get_datasec_x2(amp)
               #ampsec_y1 = get_ccdsec_y1(amp)
               #ampsec_y2 = get_ccdsec_y2(amp)
               ampsec_y1 = 1
               ampsec_y2 = stripeRows

#               hdr['AMPSEC']  = ('[%d:%d,%d:%d]' % (get_ccdsec_x1(amp),get_ccdsec_x2(amp),get_ccdsec_y1(amp),get_ccdsec_y2(amp)), 'Amplifier Section')
               hdr['AMPSEC'] = ('[%d:%d,%d:%d]' % (ampsec_x1, ampsec_x2, ampsec_y1, ampsec_y2), 'Amplifier Section (data-olny)')
               print(f"AMPSEC   = {hdr['AMPSEC']}")

               hdr['DATASEC'] = ('[%d:%d,%d:%d]' % (get_datasec_x1(amp),get_datasec_x2(amp),get_datasec_y1(amp),get_datasec_y2(amp)), 'Data Section')
               print(f"DATASEC   = {hdr['DATASEC']}")


               detCs = get_detsec_x1(ccd, amp)
               print('DEBUG: detCs =', detCs)

               hdr['DETSEC']  = ('[%d:%d,%d:%d]' % (get_detsec_x1(ccd, amp), get_detsec_x2(ccd, amp), get_detsec_y1(ccd, amp), get_detsec_y2(ccd, amp)),
                                 'Stripe Coords on Detector')
               print(f"DETSEC   = {hdr['DETSEC']}  {ccd}")


               if preCols == 0:
                   hdr['PRESEC']  = (f'[1:0,{get_presec_y1(amp)}:{get_presec_y2(amp)}]', 'No prescan')
               else: 
                   hdr['PRESEC']  = ('[%d:%d,%d:%d]' % (get_presec_x1(amp), get_presec_x2(amp), get_presec_y1(amp), get_presec_y2(amp)),
                                 'Prescan Section')
               print(f"PRESEC   = {hdr['PRESEC']}  {ccd}")

               hdr['BIASSEC'] = ('[%d:%d,%d:%d]' % (get_biassec_x1(amp), get_biassec_x2(amp), get_biassec_y1(amp), get_biassec_y2(amp)),
                                 'Bias Overscan Section')
               print(f"BIASSEC   = {hdr['BIASSEC']}  {ccd}")

#               hdr['TRIMSEC'] = ('[%d:%d,%d:%d]' % (get_trimsec_x1(amp), get_trimsec_x2(amp), get_trimsec_y1(amp), get_trimsec_y2(amp)),
#                                     'Trimmed Data Section')
               hdr['TRIMSEC'] = ('[%d:%d,%d:%d]' % (get_datasec_x1(amp),get_datasec_x2(amp),get_datasec_y1(amp),get_datasec_y2(amp)), 'Trimmed Data Section')
               print(f"TRIMSEC   = {hdr['TRIMSEC']}  {ccd}")

               hdr['FILTER'] = (filtername,'Filter Name in the beam')

               ### added by keaton03 2015-07-01       ###
               hdr['PROJID'] = (projid)
               hdr['IMAGETYP'] = (imagetyp, 'Type of observation')
               hdr['OBJECT'] = (object,'Name of object')
               hdr['OBSTYPE'] = (obstype,'Type of observation')
               hdr['RA'] = (RA,'Telescope RA')
               hdr['DEC'] = (Dec,'Telescope DEC')
               hdr['HA'] = (ha,'Hour Angle at start of obs')
               hdr['ST'] = (st,'Local Sidereal Time at start of obs')
               hdr['SECZ'] = (secz,'Secant of ZD (Airmass) at start of obs')
               hdr['ALT'] = (numALT,'Telesope Altitude (elevation) in degrees')
               az2 = az*1
               print('DEBUG: az2 =', az2)
               hdr['AZ'] = (az2,'Telescope Azimuth in degrees')

               hdr['UT'] = (ut,'Master IC reports shutter open time')
               ### ---------------------------------- ###

               # The WCS stuff - this WCS is related to the position of the device on
               # the FPA proper.  We also assign the RA/Dec of the field to the
               # center of the FPA to provide a basic close-to-real-sky WCS when the
               # MEF file is viewed in ds9 as an WCS Mosaic

               hdr['CTYPE1'] = ('RA---TAN','Coordinate Type')
               hdr['CTYPE2'] = ('DEC--TAN','Coordinate Type')
               hdr['CRVAL1'] = (CRVAL1,'Coordinate Reference Value')
               hdr['CRVAL2'] = (CRVAL2,'Coordinate Reference Values')

               # Because CCDs are read in column stripes, CRPIX1 is relative to
               # the stripe, not the parent CCD, but CRPIX2 is the same as for
               # the parent CCD.  Similarly CDi_j are the same as the parent CCD.

               hdr['CRPIX1'] = (CRPIX1[detID]-crpix1_0,'Coordinate Reference Pixel')
               hdr['CRPIX2'] = (CRPIX2[detID],'Coordinate Reference Pixel')
               hdr['CD1_1']  = (CD1_1[detID],'Coordinate Transformation Matrix')
               hdr['CD1_2']  = (CD1_2[detID],'Coordinate Transformation Matrix')
               hdr['CD2_1']  = (CD2_1[detID],'Coordinate Transformation Matrix')
               hdr['CD2_2']  = (CD2_2[detID],'Coordinate Transformation Matrix')
               # Coordinate transform keywords.  The basic document describing
               # these is "NOAO Image Data Structure Definitions"
               # (iraf.noao.edu/projects/ccdmosaic/imagedef/imagedef.html).
               # These are used by ds9 to translate the cursor position into
               # the current pixel location within the unit detector, stripe,
               # or the entire 4-detector mosaic.  To say it is mildly
               # confusing is putting entirely too optimistic a spin on
               # things.  The way the KMTN Camera system is readout in
               # stripes, and how the de-interlaced overscan and prescan are
               # recorded means the definitions for our camera are slightly
               # different than the original NOAO definition described above.
               #

               # CCD to Amplifier Transformation Matrix, which is based on
               # which pixels are read from the full active area of a single
               # detector in the mosaic.  In our context, this will convert
               # cursor position in ds9 into pixel location within the full
               # unit CCD image frame (stripe-independent).  For the flipped
               # detectors (K and N), it is pixel location in the flipped
               # (sky-oriented) frame, not the readout frame.
               #
               # ds9 displays this transform as "Amplifier" on the GUI

               #atv1 = amp*stripeCols
               #atv1 = ((amp - 1) % 8) * 1152 
               #atv1 = stripeCols + biasCols
               tile_w = stripeCols + biasCols
               atv1 = ((amp - 1) % 8 ) * tile_w
               print('DEBUG: atv1 =', atv1)
               hdr['ATV1']   = (atv1,'CCD to Amplifier Transform')
               hdr['ATV2']   = (0,'CCD to Amplifier Transform')
               hdr['ATM1_1'] = (1,'CCD to Amplifier Transform')
               hdr['ATM1_2'] = (0,'CCD to Amplifier Transform')
               hdr['ATM2_1'] = (0,'CCD to Amplifier Transform')
               hdr['ATM2_2'] = (1,'CCD to Amplifier Transform')

               # CCD to Image Transformation Matrix.  This is the recorded
               # image pixel array.  In our context, this converts the cursor
               # position in ds9 into where you are within a given stripe
               # (i.e., strip coordinates), which start with (1,1) in the
               # lower left corner, up to (1152,9232) at the upper right.  In
               # our context this is "physical" coordinates within the image
               # subsection in this extension.
               #
               # ds9 displays this transform as "Physical" on the GUI

               #ltv1 = preCols
               #ltv1 = ((amp - 1) % 8 // 4) * 48
               ltv1 = get_datasec_x1(amp) - 1
               print('DEBUG: ltv1 =', ltv1)
               hdr['LTV1']   = (ltv1,'CCD to Image Transform')
               hdr['LTV2']   = (0,'CCD to Image Transform')
               hdr['LTM1_1'] = (1,'CCD to Image Transform')
               hdr['LTM1_2'] = (0,'CCD to Image Transform')
               hdr['LTM2_1'] = (0,'CCD to Image Transform')
               hdr['LTM2_2'] = (1,'CCD to Image Transform')

               # The CCD to Detector (aka "mosaic") transform depends on
               # which CCD this is and DTV1 additionally depends on which
               # stripe in the CCD this is.  This is the only one of the
               # three that makes sense relative to the original NOAO
               # documentation in the KMTN camera context.  
               #
               # Detector (aka "mosaic") coordinates are as-if the entire
               # 4-CCD mosiac were one big pixel grid with gaps of no-data
               # between the 4 "active" areas.  Detector pixel (1,1) is the
               # first pixel of the N detector at the lower lefthand corner.
               #
               # ds9 displays this transform as "Detector" on the GUI

               dtv1 = detCs-1
               print('DEBUG: dtv1 =', dtv1)
               hdr['DTV1']   = (dtv1,'CCD to Detector Mosaic Transform')
               hdr['DTV2']   = (detR0,'CCD to Detector Mosaic Transform')
               hdr['DTM1_1'] = (1,'CCD to Detector Mosaic Transform')
               hdr['DTM1_2'] = (0,'CCD to Detector Mosaic Transform')
               hdr['DTM2_1'] = (0,'CCD to Detector Mosaic Transform')
               hdr['DTM2_2'] = (1,'CCD to Detector Mosaic Transform')

               # Last WCS bits ala IRAF

               hdr['WCSDIM']   = (2,'Coordinate System Dimensionality')
               hdr['WAT0_001'] = ('system=image','Coordinate System')
               hdr['WAT1_001'] = ('wtype=tan axtype=ra','Coordinate Type')
               hdr['WAT2_001'] = ('wtype=tan axtype=dec','Coordinate Type')

               # All done, append the stripe to the MEF.  By default
               # (convert=False), we seek to preserve the original data
               # scaling, we do this by hand instead of using the
               # fits.append() method so we can explicitly force scaling.
               # However, if convert=True, use fits.append().

#               print stripe

               if convert:
                   fits.append(mefFile,stripe,hdr)
               else:
                   f = fits.open(mefFile,mode='append',scale_back=True)
#                   print('DEBUG: f =', f)
                   hdu.data=stripe
                   hdu.header = hdr
                   if bitpix==16:
                       hdu.scale('int16',bzero=bzero,bscale=bscale)
                   elif bitpix==32:
                       hdu.scale('int32',bzero=bzero,bscale=bscale)
                   f.append(hdu)
                   f.close()


           if haveSEF[TAG]:
                   inFITS.close()





       print("- - - - - - - - - - - - - - - - - - - - - - - - - << %s END >> " % (TAG))
       print(" ")

print(" %s " % (mefFile))

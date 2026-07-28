#!/bin/csh -f

cd /PREPROC_STORAGE/d_CTIO_OBS/Y2022

sethead 20220813/KMTN*.20220813.023579.fits object="E45_f-60"
sethead 20220813/KMTN*.20220813.023580.fits object="E45_f-50"
sethead 20220813/KMTN*.20220813.023581.fits object="E45_f-40"
sethead 20220813/KMTN*.20220813.023582.fits object="E45_f-35"
sethead 20220813/KMTN*.20220813.023583.fits object="E45_f-30"
sethead 20220813/KMTN*.20220813.023584.fits object="E45_f-25"
sethead 20220813/KMTN*.20220813.023585.fits object="E45_f-15"
sethead 20220813/KMTN*.20220813.023586.fits object="E45_f-05"
sethead 20220813/KMTN*.20220813.023587.fits object="E45_f-00"
sethead 20220813/KMTN*.20220813.023588.fits object="E45_f+05"
sethead 20220813/KMTN*.20220813.023589.fits object="E45_f+15"
sethead 20220813/KMTN*.20220813.023590.fits object="E45_f+25"
sethead 20220813/KMTN*.20220813.023591.fits object="E45_f+30"
sethead 20220813/KMTN*.20220813.023592.fits object="E45_f+35"
sethead 20220813/KMTN*.20220813.023593.fits object="E45_f+40"
sethead 20220813/KMTN*.20220813.023594.fits object="E45_f+50"
sethead 20220813/KMTN*.20220813.023595.fits object="E45_f+60"

sethead 20220813/KMTN*.20220813.023596.fits object="W45_f-60"
sethead 20220813/KMTN*.20220813.023597.fits object="W45_f-50"
sethead 20220813/KMTN*.20220813.023598.fits object="W45_f-40"
sethead 20220813/KMTN*.20220813.023599.fits object="W45_f-35"
sethead 20220813/KMTN*.20220813.023600.fits object="W45_f-30"
sethead 20220813/KMTN*.20220813.023601.fits object="W45_f-25"
sethead 20220813/KMTN*.20220813.023602.fits object="W45_f-15"
sethead 20220813/KMTN*.20220813.023603.fits object="W45_f-05"
sethead 20220813/KMTN*.20220813.023604.fits object="W45_f-00"
sethead 20220813/KMTN*.20220813.023605.fits object="W45_f+05"
sethead 20220813/KMTN*.20220813.023606.fits object="W45_f+15"
sethead 20220813/KMTN*.20220813.023607.fits object="W45_f+25"
sethead 20220813/KMTN*.20220813.023608.fits object="W45_f+30"
sethead 20220813/KMTN*.20220813.023609.fits object="W45_f+35"
sethead 20220813/KMTN*.20220813.023610.fits object="W45_f+40"
sethead 20220813/KMTN*.20220813.023611.fits object="W45_f+50"
sethead 20220813/KMTN*.20220813.023612.fits object="W45_f+60"

gethead 20220813/KMTNk.*.fits projid object filter exptime fafocus alt az | grep ENG
echo
gethead 20220813/KMTN*.023612.fits projid object filter exptime fafocus alt az | grep ENG

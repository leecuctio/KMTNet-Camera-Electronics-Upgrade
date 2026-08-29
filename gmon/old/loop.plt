pause 10
reset
stats 'fw181022.dat' u 7 nooutput 
set term x11
set title 'FFT (FWHM-FOCUS-TEMP) Monitoring' 
set xdata time
set timefmt '%d:%H:%M:%S' 
set format x '%H:%M' 
set autoscale xfix
set yrange [0:12]
set y2tics
set y2range [-6.6:-4.8]
set key left top
set xlabel 'UT (2018-10-22)' 
set ylabel 'FWHM (arcsec) / T (C)' 
set y2label 'FOCUS (mm)' 
set grid
replot
reread

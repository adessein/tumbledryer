set terminal pngcairo
set output ofile
p ifile u 0:3 w l lt 1 lc 1 lw 2 t 'T°C', '' u 0:4 w l lc 3 lw 2 t '%RH'
set output

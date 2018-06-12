set terminal pngcairo
set output 'trh.png'
p 'trh.log' u 0:1 w l lt 1 lc 1 lw 2 t 'T°C', '' u 0:2 w l lc 3 lw 2 t '%RH'
set output

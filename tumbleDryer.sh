#!/bin/sh
gnuplot -e "ifile='$1'; ofile='${1%.log}.png'" tumbleDryer.gp


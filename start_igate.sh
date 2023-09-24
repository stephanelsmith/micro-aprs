#!/usr/bin/bash
#rtl_fm -f 144.390M -s 22050 -g 50 -l 0 - | pypy3 aprs_demod.py -t raw - | python aprs_is.py -c KI5TOF-10 -p 17081 -lat 29.699616621630348 -lon -95.75020574442557
pypy3 aprs_demod.py -t raw rtl_fm | python aprs_is.py -c KI5TOF-10 -p 17081 -lat 29.699616621630348 -lon -95.75020574442557

#!/usr/bin/bash
python termux_beacon.py | pypy3 aprs_mod.py -vox -t play -t -

#!/usr/bin/bash
python termux_beacon.py | python aprs_mod.py -vox | python play_samples.py

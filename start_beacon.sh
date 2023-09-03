#!/usr/bin/bash
python termux_beacon.py | python aprs_mod.py | python play_samples.py

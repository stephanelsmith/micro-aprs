
## :satellite: APRS Rx only IGate

* Rx Only IGate with APRS forwarding to APRS IS (live viewing on [aprs.fi](https://aprs.fi/)).
Note: currently the aprs_is function is somewhat hard coded for me out of convenience, can certainly be better paramerterized.

### Arguments

* Command line options showing with help flag ```-h```
```
python aprs_is.py -h
```
```
APRS IS GATEWAY
(C) Stephane Smith (KI5TOF) 2024

Usage: python aprs_is.py [OPTIONS]
aprs_is.py sends aprs commands from stdin to aprs is servers.

OPTIONS:
    -c, --call         APRS call sign
    -p, --passcode     APRS passcode (https://apps.magicbug.co.uk/passcode/)
    -lat               Beacon lat (decimal notation)
    -lon               Beacon lon (decimal notation)
    -msg               Beacon message, default: micro-aprs-modem 144.390MHz rx only APRS iGate
```

### Examples

* Send a message to APRS IS, viewable on [aprs.fi](https://aprs.fi/)
```
echo "KI5TOF>APRS:>hello world!" | python aprs_is.py -c KI5TOF -p xxxxx
```

* A 144.390MHz rx only APRS iGate
```
rtl_fm -f 144.390M -s 22050 -g 10 - | pypy3 aprs_demod.py -t - | python aprs_is.py -c CALLSIGN-10 -p xxxx -lat xxxx -lon xxxx
pypy3 aprs_demod.py -t rtl_fm | python aprs_is.py -c CALLSIGN-10 -p xxxx -lat xxxx -lon xxxx
```

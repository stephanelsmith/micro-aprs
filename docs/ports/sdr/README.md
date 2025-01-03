# :radio: SDR based examples

SDRs are a great way to interface with micro-aprs.  I've used the [RTL-SDR]([https://manpages.ubuntu.com/manpages/trusty/man1/rtl_fm.1.html](https://www.rtl-sdr.com/buy-rtl-sdr-dvb-t-dongles/)) as it's inexpensive and works pretty well!  Paired with the [rtl-sdr library tools](https://launchpad.net/ubuntu/trusty/+package/rtl-sdr), it's very easy to get started!  

These examples take advantage of input/output piping to feed audio samples into micro-aprs live.

## :sound: Live APRS Decode with RTL-SDR

* Live decode of APRS on 144.39MHz using rtl_fm:
```
rtl_fm -f 144.390M -s 22050 -g 1 - | python aprs_demod.py -t -
```

## :satellite: APRS Rx only IGate
Rx Only IGate with APRS forwarding to APRS IS (live viewing on [aprs.fi](https://aprs.fi/)).
Note: currently the aprs_is function is somewhat hard coded for me out of convenience, can certainly be better paramerterized.

Command line options showing with help flag ```-h```
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

### :round_pushpin: Send a message to APRS IS, viewable on [aprs.fi](https://aprs.fi/)
```
echo "KI5TOF>APRS:>hello world!" | python aprs_is.py -c KI5TOF -p xxxxx
```

### 🚪 A 144.390MHz rx only APRS iGate
```
rtl_fm -f 144.390M -s 22050 -g 10 - | pypy3 aprs_demod.py -t - | python aprs_is.py -c CALLSIGN-10 -p xxxx -lat xxxx -lon xxxx
```

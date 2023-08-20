


# Micro APRS MODEM

A python/micropython based library for encoding/decoding, modulating/demodulating APRS/AX.25 packets in AFSK.  
<!---
![AFSK hello world](docs/afsk_hello.png?raw=true "AFSK hello")
--->
<p align="center">
  <img src="https://github.com/stephanelsmith/micro-aprs/blob/master/docs/demod/corr_total.gif?raw=true" alt=""/>
</p>

The purpose of this library is to thread-the-needle of both enabling APRS/AX.25/AFSK from PC to microcontroller while maintaining portability and readability of python.  This library is optimized for embedded systems, especially [micropython supported targets and platforms ](https://github.com/micropython/micropython#supported-platforms--architectures) and small computers, not to mention Cpython and Pypy! 

In practice this means we:
* Avoid floating point and math libraries and dependencies in critical sections.  
	* :+1: Integer math only
	* :+1: NO external libraries (numpy/scipy/pandas).
* Special care for memory allocation
	* :+1: Pre-computing buffer/array sizes and modifying in place
	* :-1: Dynamically appending items to a list
* Single threaded, multitask friendly
	* :+1::+1: Asyncio


### **Micro-Aprs decodes 1000+ error-free frames on the [TNC CD Track 2](http://wa8lmf.net/TNCtest/).  That's **1010** :eyes: in a balanced mode at **1014** :fireworks: in a more computational intensive mode!**

(TNC CD Track 2 is the universal test for APRS demod, [this performance is very good!](https://github.com/wb2osz/direwolf/blob/dev/doc/WA8LMF-TNC-Test-CD-Results.pdf))


## :mortar_board: Tutorials

As many who've gone down this path have mentioned, there's really just not a lot of information out there covering these topics.  I hope these tutorial sections will provide you additional information on getting started!
* [AFSK Demodulation](docs/demod/README.md). Convert raw AFSK samples to bits.
* [AFSK Modulation](docs/mod/README.md). Convert byte arrays to AFSK samples
* [AX25/APRS Encoding and Decoding](docs/encdec/README.md). Step-by-step encoding/decoding APRS and AX25.
* [144.39MHz 1/4 Wave Ground Plane Antenna Design](docs/ant/README.md).


## :snake: Python Compatibility
Care has been taken to make the source fully compatible across target python versions:
* Python (for the lazy)
* Micropython (for embedded)
* Pypy3 (for speed!)


## :satellite: APRS to AFSK Modulation

```aprs_mod.py``` provides conversion from APRS string(s) into raw 16 bit signed integer raw format with a default sampling rate 22050. 

### Arguments

* Command line options showing with help flag ```-h```
```
python aprs_mod.py -h
```
```
APRS MOD
(C) Stephane Smith (KI5TOF) 2023

Usage:
aprs_mod.py [options] (-t outtype outfile) (-t intype infile)
aprs_mod.py [options] (-t intype infile)
aprs_mod.py [options]
aprs_mod.py

OPTIONS:
-r, --rate       22050 (default)
-v, --verbose    verbose intermediate output to stderr

-t INPUT TYPE OPTIONS:
intype       'aprs' (default)
infile       '-' (default)

-t OUTPUT TYPE OPTIONS:
outtype       'raw'
outfile       '-' (default) | 'null' (no output)
```

### Examples

* aprs_mod.py micropython generated wav file, decode with:
	* Direwolf ```atest```
 	* Multimon-ng
  	* aprs_demod
```
echo "KI5TOF>APRS:>hello world!" | micropython aprs_mod.py | sox -t raw -b 16 -e signed-integer -c 1 -v 1.0 -r 22050 -  -t wav test.wav
atest test.wav
sox -t wav test.wav -t raw -b 16 -e signed-integer -c 1 -r 22050 - | multimon-ng -t raw -A -a AFSK1200 -
sox -t wav test.wav -t raw -b 16 -e signed-integer -c 1 -r 22050 - | micropython aprs_demod.py -t raw -
```

* ```aprs_mod.py``` python inline decode
```
echo "KI5TOF>APRS:>hello world!" | python aprs_mod.py -t raw - -t aprs - | multimon-ng -t raw -A -a AFSK1200 -
echo "KI5TOF>APRS:>hello world!" | python aprs_mod.py | multimon-ng -t raw -A -a AFSK1200 -
echo "KI5TOF>APRS:>hello world!" | python aprs_mod.py -v | python aprs_demod.py -v -t raw -
```


## :satellite: AFSK Demodulation to APRS Strings

```aprs_demod.py``` reads in raw 16 bit signed integers from standard input or file and output detected APRS strings.


### Arguments

* Command line options showing with help flag ```-h```
```
python aprs_demod.py -h
```
```
APRS DEMOD
(C) Stephane Smith (KI5TOF) 2023

Usage:
aprs_demod.py [options] (-t outtype outfile) (-t intype infile)
aprs_demod.py [options] (-t intype infile)
aprs_demod.py [options]
aprs_demod.py

OPTIONS:
-r, --rate       22050 (default)
-v, --verbose    verbose intermediate output to stderr

-t INPUT TYPE OPTIONS:
intype       'raw' (default)
infile       '-' (default) | raw file

-t OUTPUT TYPE OPTIONS:
outtype       'aprs'
outfile       '-' (default)
```

### Examples

* Demod with python, micropython, and pypy
```
echo "KI5TOF>APRS:>hello world!" | python aprs_mod.py -v | python aprs_demod.py -v -t raw -
echo "KI5TOF>APRS:>hello world!" | micropython aprs_mod.py -v | micropython aprs_demod.py -v -t raw -
echo "KI5TOF>APRS:>hello world!" | pypy3 aprs_mod.py -v | pypy3 aprs_demod.py -v -t raw -
```

* Decode Direwolf generated sample
```
gen_packets -r 22050 -o test.wav
sox -t wav test.wav -t raw -b 16 -e signed-integer -c 1 -r 22050 - | micropython aprs_demod.py -t raw -
```
```
WB2OSZ-11>TEST:,The quick brown fox jumps over the lazy dog!  1 of 4
WB2OSZ-11>TEST:,The quick brown fox jumps over the lazy dog!  2 of 4
WB2OSZ-11>TEST:,The quick brown fox jumps over the lazy dog!  3 of 4
WB2OSZ-11>TEST:,The quick brown fox jumps over the lazy dog!  4 of 4
```

* Decode [International Space Station flyby recording](https://inst.eecs.berkeley.edu/~ee123/sp14/lab3/ISSpkt.wav)
```
wget https://inst.eecs.berkeley.edu/~ee123/sp14/lab3/ISSpkt.wav
sox -t wav ISSpkt.wav -t raw -b 16 -e signed-integer -c 1 -r 22050 - | python aprs_demod.py -t raw -
```
```
RS0ISS>CQ:>ARISS - International Space Station
```

* Decode [TNC Test CD](http://wa8lmf.net/TNCtest/)
    * Download and convert TNC tests to .wav/.flac files
    * Using bchunk (apt-get install bchunk)
    * Run track 2 test
```
wget http://wa8lmf.net/TNCtest/TNC_Test_CD_Ver-1.1.zip
bchunk -w TNC_Test_Ver-1.1.bin TNC_Test_Ver-1.1.cue tnc_test
```
```
sox -t wav test/tnc_test02.wav -t raw -b 16 -e signed-integer -c 1 -r 22050 - | python aprs_demod.py -t raw -
```

## :radio: Live APRS Decode with RTL-SDR

* Live decode of APRS on 144.39MHz using rtl_fm:
```
rtl_fm -f 144.390M -s 22050 -g 1 - | python aprs_demod.py -t raw -
```

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
(C) Stephane Smith (KI5TOF) 2023

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

* Send a message to APRS IS, viewable on [aprs.fi])https://aprs.fi/)
```
echo "KI5TOF>APRS:>hello world!" | python aprs_is.py -c KI5TOF -p xxxxx
```

* A 144.390MHz rx only APRS iGate
```
rtl_fm -f 144.390M -s 22050 -g 10 - | pypy3 aprs_demod.py -t raw - | python aprs_is.py -c KI5TOF -p xxxx -lat xxxx -lon xxxx
```


## :raised_hands: Acknowledgements
- [Micropython](https://github.com/micropython/micropython) project
- [Direwolf TNC](https://github.com/wb2osz/direwolf)


## License
MIT License



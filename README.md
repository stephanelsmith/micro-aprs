


# Micro APRS MODEM

A python/micropython based library for encoding/decoding, modulating/demodulating APRS/AX.25 packets in AFSK audio.  
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

As many who've gone down this path have mentioned, there's surprisingly little useful information out there covering these topics.  I hope these tutorial sections will provide you additional information on getting started!
* [AFSK Demodulation](docs/demod/README.md). Convert raw AFSK samples to bits.
* [AFSK Modulation](docs/mod/README.md). Convert byte arrays to AFSK samples
* [AX25/APRS Encoding and Decoding](docs/encdec/README.md). Step-by-step encoding/decoding APRS and AX25.
* [144.39MHz 1/4 Wave Ground Plane Antenna Design](docs/ant/README.md).
* [Building Micrpython Firware](docs/ports/README.md)
* [ESP32-S3 Implementation Considerations - Missing DAC](docs/ports/dac/README.md)


## :radio: Ports and Examples
* [CLI with Python/Pypy](docs/ports/cli/README.md)
* [CLI with Micropython](docs/ports/upy/README.md)
* [TinyS3](docs/ports/tinys3/README.md), a quality and accessible esp32s3 board.
* [LilyGo T-TWR Plus](docs/ports/lilygottwr/README.md), a commerically available esp32s3 board with SA868 Wireless Transceiver.


## :satellite: APRS to AFSK Modulation

```aprs_mod.py``` provides conversion from APRS string(s) into raw 16 bit signed integer raw format with a default sampling rate 22050. 

### Arguments

* Command line options showing with help flag ```-h```
```
python aprs_mod.py -h
```
```
APRS MOD
(C) Stephane Smith (KI5TOF) 2024

Usage:
aprs_mod.py [options] (-t outfile) (-t infile)
aprs_mod.py [options] (-t infile)
aprs_mod.py [options]
aprs_mod.py

OPTIONS:
-r, --rate       22050 (default)
-vox, --vox      Vox mode, pad header flags to activate radio vox
-v, --verbose    verbose intermediate output to stderr

-t INPUT TYPE OPTIONS:
intype       aprs strings
infile       '-' (default)

-t OUTPUT TYPE OPTIONS:
outtype       raw 16 bit samples
outfile       '-' (default) | 'null' (no output) | '*.wav' (wave file) | 'play' play audio
```

### Examples

* aprs_mod.py micropython generated wav file, decode with:
	* Direwolf ```atest```
 	* Multimon-ng
  	* aprs_demod
```
echo "KI5TOF>APRS:>hello world!" | micropython aprs_mod.py | sox -t raw -b 16 -e signed-integer -c 1 -v 1.0 -r 22050 -  -t wav test/test.wav
echo "KI5TOF>APRS:>hello world!" | python aprs_mod.py -vox -t test/test.wav -t -
atest test/test.wav
sox -t wav test/test.wav -t raw -b 16 -e signed-integer -c 1 -r 22050 - | multimon-ng -t raw -A -a AFSK1200 -
sox -t wav test/test.wav -t raw -b 16 -e signed-integer -c 1 -r 22050 - | micropython aprs_demod.py -t -
echo "KI5TOF>APRS:>hello world!" | python aprs_mod.py -vox -t play -t -
```

* ```aprs_mod.py``` python inline decode
```
echo "KI5TOF>APRS:>hello world!" | python aprs_mod.py -t - -t aprs - | multimon-ng -t raw -A -a AFSK1200 -
echo "KI5TOF>APRS:>hello world!" | python aprs_mod.py | multimon-ng -t raw -A -a AFSK1200 -
echo "KI5TOF>APRS:>hello world!" | python aprs_mod.py -v | python aprs_demod.py -v -t -
echo "KI5TOF>APRS:>hello world!" | micropython aprs_mod.py -v | micropython aprs_demod.py -v -t -
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
(C) Stephane Smith (KI5TOF) 2024

Usage:
aprs_demod.py [options] (-t outfile) (-t infile)
aprs_demod.py [options] (-t infile)
aprs_demod.py [options]
aprs_demod.py

OPTIONS:
-r, --rate       22050 (default)
-v, --verbose    verbose intermediate output to stderr

-t INPUT TYPE OPTIONS:
intype       'raw' 16 bit signed samples
infile       '-' (default stdin) | 'filename.raw' raw file | 'rtl_fm' input from rtl_fm

-t OUTPUT TYPE OPTIONS:
outtype       'aprs' strings
outfile       '-' (default stdout)
```

### Examples

* Demod with python, micropython, and pypy
```
echo "KI5TOF>APRS:>hello world!" | python aprs_mod.py -v | python aprs_demod.py -v -t -
echo "KI5TOF>APRS:>hello world!" | micropython aprs_mod.py -v | micropython aprs_demod.py -v -t -
echo "KI5TOF>APRS:>hello world!" | pypy3 aprs_mod.py -v | pypy3 aprs_demod.py -v -t -
```

* Decode Direwolf generated sample
```
gen_packets -r 22050 -o test/test.wav
sox -t wav test/test.wav -t raw -b 16 -e signed-integer -c 1 -r 22050 - | micropython aprs_demod.py -t -
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
sox -t wav ISSpkt.wav -t raw -b 16 -e signed-integer -c 1 -r 22050 - | python aprs_demod.py -t -
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
sox -t wav test/tnc_test02.wav -t raw -b 16 -e signed-integer -c 1 -r 22050 - | python aprs_demod.py -t -
```

## :radio: Live APRS Decode with RTL-SDR

* Live decode of APRS on 144.39MHz using rtl_fm:
```
rtl_fm -f 144.390M -s 22050 -g 1 - | python aprs_demod.py -t -
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

## :iphone: Termux (Android) based APRS Beacon

* One goal is use a cell phone to generate beacon audio samples that can then be passed two a handy radio.  This is accomplished using [Termux](https://termux.dev/en/), a rad feature packed terminal for phones.  You will need to install it from F-Droid and install Termux-Api, which allows for fetching the GPS points. In termux, you can install python3, pypy3, sox, screen and any other goodies that suit your fancy.
* Modulate and play APRS becaons messages.  You will need:
  * Type-C to audio cable connected to the mic of your radio.  I opted for one with additional power connector.  In the developer settings for Android, I set screen to always be on when plugged in.
  * [3.5 mm TRS to Dual 3.5 mm TSF Stereo Breakout Cable](https://www.amazon.com/gp/product/B000068O5H/ref=ppx_yo_dt_b_asin_title_o06_s00?ie=UTF8&psc=1). The mic connector only uses the tip connector, the rest are grounded.
  * A 3.5 mm to 2.5 mm jumper.  My handy radio mic input is 2.5mm.
  * For my radio, I also needed to AC couple the the mic pin TIP like so. I couldn't find any suitable cables, so got the soldering iron out!  Not difficult!
<p align="center">
  <img src="https://github.com/stephanelsmith/micro-aprs/blob/master/docs/termux/ioqNL.png?raw=true" alt=""/>
</p>


### Examples
To be run in Termux.
 
* Fetch GPS points and generate beacon APRS messages 
```
python termux_beacon.py
```

* Play APRS beacon messages to radio
```
python termux_beacon.py | python aprs_mod.py -vox -t play -t -
```

## :bulb: Future Work
* Full integration on embedded system with MicroPython
  * I2S embedded audio interfacing
* Rx/Tx digipeating
* Deploy as a :balloon: [HAB](https://amateur.sondehub.org/) payload!

## :raised_hands: Acknowledgements
- [Micropython](https://github.com/micropython/micropython) project
- [Direwolf TNC](https://github.com/wb2osz/direwolf)


## License
GNU General Public License v3.0



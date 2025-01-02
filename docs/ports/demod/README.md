
## :loud_sound: AFSK Demodulation to APRS Strings

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

* Demod with verbose output (-v flag).
```
echo "KI5TOF>APRS:>hello world!" | python aprs_mod.py -v | python aprs_demod.py -v -t -
```

* Decode Direwolf generated sample
```
gen_packets -r 22050 -o test/test.wav
sox -t wav test/test.wav -t raw -b 16 -e signed-integer -c 1 -r 22050 - | python aprs_demod.py -t -
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


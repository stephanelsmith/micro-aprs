
# Decode AFSK audio samples to APRS strings

```aprs_demod.py``` reads in raw 16 bit signed little endian integers and outputs AX25 APRS strings.


### Basic usage
```
python aprs_demod.py -h
```
```
APRS DEMOD
© Stéphane Smith (KI5TOF) 2025

Usage:
aprs_demod.py [options] (-t outfile) (-t infile)
aprs_demod.py [options] (-t infile)
aprs_demod.py [options]
aprs_demod.py

OPTIONS:
-r, --rate       22050 (default)
-v, --verbose    verbose intermediate output to stderr

DETAIL DEBUG MODE, output samples at specific stages within pipeline. Nominall use this
option to create wav files at each step and view them in audacity to see what's up.
Stages: input, bandpass filter, correlator, and lowpass filter.
-d, --debug_samples 'in' | 'bpf' | 'cor' | 'lpf'

-t INPUT TYPE OPTIONS:
intype       's16' | 'u16'
infile       '-' (default stdin) | 'filename.raw' raw file | 'rtl_fm' input from rtl_fm

-t OUTPUT TYPE OPTIONS:
outtype       'aprs' strings
outfile       '-' (default stdout)
```

### Inline encode+decode pipeline with verbose output
```
echo "KI5TOF>APRS:>hello world!" | python aprs_mod.py | python aprs_demod.py -v -t -
```
```
frame
===== DEMOD frame ======
0000  7e 41 05 25 65 02 02 06   01111110 01000001 00000101 00100101 01100101 00000010 00000010 00000110   ~A-%e---
0008  69 49 56 15 79 31 86 c0   01101001 01001001 01010110 00010101 01111001 00110001 10000110 11000000   iIV-y1--
0016  0f 7c 0b 53 1b 1b 7b 02   00001111 01111100 00001011 01010011 00011011 00011011 01111011 00000010   -|-S--{-
0024  77 7b 27 1b 13 42 72 f0   01110111 01111011 00100111 00011011 00010011 01000010 01110010 11110000   w{'--Br-
0032  3f 00 -- -- -- -- -- --   00111111 00000000 -------- -------- -------- -------- -------- --------   ?-------
-un-stuffed-
0000  7e 41 05 25 65 02 02 06   01111110 01000001 00000101 00100101 01100101 00000010 00000010 00000110   ~A-%e---
0008  69 49 56 15 79 31 86 c0   01101001 01001001 01010110 00010101 01111001 00110001 10000110 11000000   iIV-y1--
0016  0f 7c 16 a6 36 36 f6 04   00001111 01111100 00010110 10100110 00110110 00110110 11110110 00000100   -|--66--
0024  ee f6 4e 36 26 84 e5 e0   11101110 11110110 01001110 00110110 00100110 10000100 11100101 11100000   --N6&---
0032  7e 00 -- -- -- -- -- --   01111110 00000000 -------- -------- -------- -------- -------- --------   ~-------
-un-reversed (ax25)-
0000  7e 82 a0 a4 a6 40 40 60   01111110 10000010 10100000 10100100 10100110 01000000 01000000 01100000   ~----@@`
0008  96 92 6a a8 9e 8c 61 03   10010110 10010010 01101010 10101000 10011110 10001100 01100001 00000011   --j---a-
0016  f0 3e 68 65 6c 6c 6f 20   11110000 00111110 01101000 01100101 01101100 01101100 01101111 00100000   ->hello
0024  77 6f 72 6c 64 21 a7 07   01110111 01101111 01110010 01101100 01100100 00100001 10100111 00000111   world!--
0032  7e 00 -- -- -- -- -- --   01111110 00000000 -------- -------- -------- -------- -------- --------   ~-------
[1] KI5TOF>APRS:>hello world!
```


### 🐺 Decode Direwolf generated audio sample
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

### 🛰️ Decode [International Space Station flyby recording](https://inst.eecs.berkeley.edu/~ee123/sp14/lab3/ISSpkt.wav)
```
wget https://inst.eecs.berkeley.edu/~ee123/sp14/lab3/ISSpkt.wav
sox -t wav ISSpkt.wav -t raw -b 16 -e signed-integer -c 1 -r 22050 - | python aprs_demod.py -t -
```
```
RS0ISS>CQ:>ARISS - International Space Station
```

### Decode [TNC Test CD](http://wa8lmf.net/TNCtest/)
Download and convert TNC tests to .wav/.flac files
```
wget http://wa8lmf.net/TNCtest/TNC_Test_CD_Ver-1.1.zip
unzip TNC_Test_CD_Ver-1.1.zip
sudo apt-get install bchunk
bchunk -w TNC_Test_Ver-1.1.bin TNC_Test_Ver-1.1.cue tnc_test
```
```
sox -t wav test/tnc_test02.wav -t raw -b 16 -e signed-integer -c 1 -r 22050 - | python aprs_demod.py -t -
```


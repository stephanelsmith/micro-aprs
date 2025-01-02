
# Encoding AX25 APRS to AFSK :loud_sound:

```aprs_mod.py``` parses input AX25 APRS strings and outputs AFSK samples in signed 16 bit little endian format.  The most common input and output interface is using pipes (few other options available as well).

## :loud_sound: APRS to AFSK audio samples

```aprs_mod.py``` provides conversion from APRS string(s) into raw 16 bit signed integer raw format with a default sampling rate 22050. 

### Basic usage
```
python aprs_mod.py -h
```
```
APRS MOD
© Stéphane Smith (KI5TOF) 2025

aprs_mod.py parses input AX25 APRS strings and outputs AFSK samples in signed 16 bit little endian format.

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
infile       '-' (default)

-t OUTPUT TYPE OPTIONS:
outfile       '-' (default) | 'null' (no output) | '*.wav' (wave file) | 'play' play audio
```

### Encode AX25 APRS string in verbose mode
```-v``` verbose mode is designed to show the intermediate steps (on stderr).  For this example, we suppress output (setting stdout to null).
```
echo "KI5TOF>APRS:>hello world!" | python aprs_mod.py -v -t null -t -
```
```
# APRS MOD
# RATE 22050
# IN   -
# OUT  null
===== MOD >>>>> KI5TOF>APRS:>hello world!
--ax25--
0000  7e 82 a0 a4 a6 40 40 60   01111110 10000010 10100000 10100100 10100110 01000000 01000000 01100000   ~----@@`
0008  96 92 6a a8 9e 8c 61 03   10010110 10010010 01101010 10101000 10011110 10001100 01100001 00000011   --j---a-
0016  f0 3e 68 65 6c 6c 6f 20   11110000 00111110 01101000 01100101 01101100 01101100 01101111 00100000   ->hello
0024  77 6f 72 6c 64 21 a7 07   01110111 01101111 01110010 01101100 01100100 00100001 10100111 00000111   world!--
0032  7e -- -- -- -- -- -- --   01111110 -------- -------- -------- -------- -------- -------- --------   ~-------
-reversed-
0000  7e 41 05 25 65 02 02 06   01111110 01000001 00000101 00100101 01100101 00000010 00000010 00000110   ~A-%e---
0008  69 49 56 15 79 31 86 c0   01101001 01001001 01010110 00010101 01111001 00110001 10000110 11000000   iIV-y1--
0016  0f 7c 16 a6 36 36 f6 04   00001111 01111100 00010110 10100110 00110110 00110110 11110110 00000100   -|--66--
0024  ee f6 4e 36 26 84 e5 e0   11101110 11110110 01001110 00110110 00100110 10000100 11100101 11100000   --N6&---
0032  7e 00 00 00 00 00 00 00   01111110 00000000 00000000 00000000 00000000 00000000 00000000 00000000   ~-------
0040  00 -- -- -- -- -- -- --   00000000 -------- -------- -------- -------- -------- -------- --------   --------
-bit stuffed-
0000  7e 41 05 25 65 02 02 06   01111110 01000001 00000101 00100101 01100101 00000010 00000010 00000110   ~A-%e---
0008  69 49 56 15 79 31 86 c0   01101001 01001001 01010110 00010101 01111001 00110001 10000110 11000000   iIV-y1--
0016  0f 7c 0b 53 1b 1b 7b 02   00001111 01111100 00001011 01010011 00011011 00011011 01111011 00000010   -|-S--{-
0024  77 7b 27 1b 13 42 72 f0   01110111 01111011 00100111 00011011 00010011 01000010 01110010 11110000   w{'--Br-
0032  3f 00 00 00 00 00 00 00   00111111 00000000 00000000 00000000 00000000 00000000 00000000 00000000   ?-------
0040  00 -- -- -- -- -- -- --   00000000 -------- -------- -------- -------- -------- -------- --------   --------
--nrzi-- bits 32 bytes 4 remain 0
11111110 11111110 11111110 11111110

--nrzi-- bits 265 bytes 33 remain 1
11111110 11010100 10101100 10010011 00010011 01010110 10101001 01010001 00011011 00100100
11001110 10110011 00000100 10001011 10101110 00101010 10100000 11111101 01011000 11001000
10111000 10111000 11111000 10101001 00001111 00000111 01101111 01000111 01001000 11010110
11110110 00001010 10000000 1

--nrzi-- bits 32 bytes 4 remain 0
00000001 00000001 00000001 00000001
```

### Generate AFSK audio file
Generate wave file via ```sox```.
```
echo "KI5TOF>APRS:>hello world!" | python aprs_mod.py | sox -t raw -b 16 -e signed-integer -c 1 -v 1.0 -r 22050 - -t wav test/test.wav
```

Wave file as output.
```
echo "KI5TOF>APRS:>hello world!" | python aprs_mod.py -t test/test.wav -t -
```

Decode wave file using [Direwolf (atest)](https://github.com/wb2osz/direwolf), [multimon-ng](https://github.com/EliasOenal/multimon-ng), and [aprs_demod.py](https://github.com/stephanelsmith/micro-aprs/tree/master/docs/ports/demod).
```
atest test/test.wav
sox -t wav test/test.wav -t raw -b 16 -e signed-integer -c 1 -r 22050 - | multimon-ng -t raw -A -a AFSK1200 -
sox -t wav test/test.wav -t raw -b 16 -e signed-integer -c 1 -r 22050 - | python aprs_demod.py -t -
```

### Inline encode+decode pipeline
```
echo "KI5TOF>APRS:>hello world!" | python aprs_mod.py | python aprs_demod.py -t -
```
```
# APRS MOD
# RATE 22050
# IN   -
# OUT  -
# APRS DEMOD
# RATE 22050
# IN   -
# OUT  -
[1] KI5TOF>APRS:>hello world!
```

### Multiple APRS message encode+decode pipeline
With verbose output enabled on output
```
cat test/aprs.txt | python aprs_mod.py | python aprs_demod.py -t -
```
```
# APRS DEMOD
# RATE 22050
# IN   -
# OUT  -
# APRS MOD
# RATE 22050
# IN   -
# OUT  -
[1] KI5TOF>APRS:hello world!
[2] KI5TOF>APRS,WIDE2-1,WIDE1-1:hello world1
[3] KI5TOF>APRS,WIDE2-1,WIDE1-1:hello world2
[4] KI5TOF>APRS,WIDE2-1,WIDE1-1:hello world3
```


# :loud_sound: Encoding AX25 APRS to AFSK 

```aprs_mod.py``` parses input AX25 APRS strings and outputs AFSK samples in signed 16 bit little endian format.  The most common input and output interface is using pipes (few other options available as well).

### 🫰 Basic usage
From the ```micro-aprs/src``` folder, try
```
python aprs_mod.py -h
```
```
APRS MOD
© Stéphane Smith (KW5O) 2026

aprs_mod.py parses input AX25 APRS strings and outputs AFSK samples in signed 16 bit little endian format.

Usage:
aprs_mod.py [options] (-t outfile) (-t infile)
aprs_mod.py [options] (-t infile)
aprs_mod.py [options]
aprs_mod.py

OPTIONS:
-r, --rate       22050 (default)
-vhf             VHF mode, space:2200 mark:1200, baud:1200 (default)
-hf              HF mode, space:1600 mark:1400, baud:300
-vox, --vox      Vox mode, pad header flags to activate radio vox
-v, --verbose    verbose intermediate output to stderr

-t INPUT TYPE OPTIONS:
infile       '-' (default)

-t OUTPUT TYPE OPTIONS:
outfile       '-' (default) | 'null' (no output) | '*.wav' (wave file) | 'play' play audio
```

### 📝 Encode AX25 APRS string in verbose mode
```-v``` verbose mode is designed to show the intermediate steps (on stderr).  For this example, we suppress output (setting stdout to null).
```
echo "KW5O>APRS:>hello world!" | python aprs_mod.py -v -t null -t -
```
```
# APRS MOD
# RATE 22050
# IN   -
# OUT  null
===== MOD >>>>> b'KW5O>APRS:>hello world!'
--ax25--
0000  7e 82 a0 a4 a6 40 40 60   01111110 10000010 10100000 10100100 10100110 01000000 01000000 01100000   ~----@@`
0008  96 ae 6a 9e 40 40 61 03   10010110 10101110 01101010 10011110 01000000 01000000 01100001 00000011   --j-@@a-
0016  f0 3e 68 65 6c 6c 6f 20   11110000 00111110 01101000 01100101 01101100 01101100 01101111 00100000   ->hello
0024  77 6f 72 6c 64 21 95 cc   01110111 01101111 01110010 01101100 01100100 00100001 10010101 11001100   world!--
0032  7e -- -- -- -- -- -- --   01111110 -------- -------- -------- -------- -------- -------- --------   ~-------
-reversed-
0000  7e 41 05 25 65 02 02 06   01111110 01000001 00000101 00100101 01100101 00000010 00000010 00000110   ~A-%e---
0008  69 75 56 79 02 02 86 c0   01101001 01110101 01010110 01111001 00000010 00000010 10000110 11000000   iuVy----
0016  0f 7c 16 a6 36 36 f6 04   00001111 01111100 00010110 10100110 00110110 00110110 11110110 00000100   -|--66--
0024  ee f6 4e 36 26 84 a9 33   11101110 11110110 01001110 00110110 00100110 10000100 10101001 00110011   --N6&--3
0032  7e 00 00 00 00 00 00 00   01111110 00000000 00000000 00000000 00000000 00000000 00000000 00000000   ~-------
0040  00 -- -- -- -- -- -- --   00000000 -------- -------- -------- -------- -------- -------- --------   --------
-bit stuffed-
0000  7e 41 05 25 65 02 02 06   01111110 01000001 00000101 00100101 01100101 00000010 00000010 00000110   ~A-%e---
0008  69 75 56 79 02 02 86 c0   01101001 01110101 01010110 01111001 00000010 00000010 10000110 11000000   iuVy----
0016  0f 7c 0b 53 1b 1b 7b 02   00001111 01111100 00001011 01010011 00011011 00011011 01111011 00000010   -|-S--{-
0024  77 7b 27 1b 13 42 54 99   01110111 01111011 00100111 00011011 00010011 01000010 01010100 10011001   w{'--BT-
0032  bf 00 00 00 00 00 00 00   10111111 00000000 00000000 00000000 00000000 00000000 00000000 00000000   --------
0040  00 -- -- -- -- -- -- --   00000000 -------- -------- -------- -------- -------- -------- --------   --------
--nrzi-- bits 32 bytes 4 remain 0
11111110 11111110 11111110 11111110

--nrzi-- bits 265 bytes 33 remain 1
11111110 11010100 10101100 10010011 00010011 01010110 10101001 01010001 00011011 00001100
11001110 11111011 01010110 10101001 10101110 00101010 10100000 11111101 01011000 11001000
10111000 10111000 11111000 10101001 00001111 00000111 01101111 01000111 01001000 11010110
11001101 10111011 10000000 1

--nrzi-- bits 32 bytes 4 remain 0
00000001 00000001 00000001 00000001
```

### 〰️ Generate AFSK audio file
Generate wave file via ```sox```.
```
echo "KW5O>APRS:>hello world!" | python aprs_mod.py | sox -t raw -b 16 -e signed-integer -c 1 -v 1.0 -r 22050 - -t wav test/test.wav
```

Wave file as output.
```
echo "KW5O>APRS:>hello world!" | python aprs_mod.py -t test/test.wav -t -
```

Decode wave file using [Direwolf (atest)](https://github.com/wb2osz/direwolf), [multimon-ng](https://github.com/EliasOenal/multimon-ng), and [aprs_demod.py](https://github.com/stephanelsmith/micro-aprs/tree/master/docs/ports/demod).
```
atest test/test.wav
sox -t wav test/test.wav -t raw -b 16 -e signed-integer -c 1 -r 22050 - | multimon-ng -t raw -A -a AFSK1200 -
sox -t wav test/test.wav -t raw -b 16 -e signed-integer -c 1 -r 22050 - | python aprs_demod.py -t -
```

### 🛹 Inline encode+decode pipeline
```
echo "KW5O>APRS:>hello world!" | python aprs_mod.py | python aprs_demod.py -t -
```
```
[1] KW5O>APRS:>hello world!
```

### 🔩 Multiple APRS message encode+decode pipeline
With verbose output enabled on output
```
cat test/aprs.txt | python aprs_mod.py | python aprs_demod.py -t -
```
```
[1] KW5O>APRS:hello world!
[2] KW5O>APRS,WIDE2-1,WIDE1-1:hello world1
[3] KW5O>APRS,WIDE2-1,WIDE1-1:hello world2
[4] KW5O>APRS,WIDE2-1,WIDE1-1:hello world3
```

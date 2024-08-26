# Encoding and Decoding AX25 and APRS messages

I struggled to find solid examples, especially regarding the order of operations for encoding/decoding AX25 frames to AFSK samples (spoiler alert it's: byte reverse, bit stuff, NRZI).  For anyone else looking for a definitive answer, ```aprs_mod.py``` and ```aprs_demod.py``` have a verbose mode which outputs the intermediate steps to stderr.  This way you should have no problem providing your inputs and compare intermediate steps in addition to the final output.

## Encoding APRS messages to AX25 format

For encoding APRS and AX25, there are in fact lots of great references which document this in detail, including:
* [The best readable reference covering AX25 Frame.](https://www.mssl.ucl.ac.uk/~mcrw/QB50/Documents/11-%20QB50-EPFL-SSC-SCS-ICD-AX.25-TFF-3-1.pdf)
* [Direwolf's packet assembler is a great refernce and well commented](https://github.com/wb2osz/direwolf/blob/master/src/ax25_pad.c)
* [Not Black Magic HDLC/AX25 was helpful](https://notblackmagic.com/bitsnpieces/ax.25/)

## Encoding AX25 to Output Samples for Modulation

To run the examples, change your working directry to the src folder.

Here are the steps, in order, to generate AFSK samples:
- Convert to AX25 bytes
- Reverse the bytes
- Stuff bits
- NRZI

With ```aprs_mod.py```, we flip the verbose option with ```-v```.  The following parameters ```-t null null -t aprs -``` specify the output is null and the input is of type APRS from stdin.

```
echo "KI5TOF>APRS:>hello world!" | python aprs_mod.py -v -t null null -t aprs -
```

The result:
```
# APRS MOD
# RATE 22050
# IN   aprs -
# OUT  null null
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

To note:
- There are many extra padded zero bytes added for bit-stuffing.  This is done to accomodate the extra stuffed bits.  The total number of bits to send is tracked and those 0s are not actually sent out.
- Currently, we add 4 AX25 header bytes before and after the message.  This is done so Direwolf and Multimon-NG clock recovery have enough to chew on to decode the message.
- NRZI is actually done very close to the output, the reason being is that it operation retains a state variable.  That is, if you do a back-to-back encode, it is important the NRZI state is retained _between_ messages. 


## Decoding Bit Stream to AX25 Byte Array

Once you got encode, decode is easy, just the flip.  We can again use out utilities, this time piping the raw samples from ```aprs_mod.py``` into ```aprs_demo.py```, again with the verbose option.

```
echo "KI5TOF>APRS:>hello world!" | python aprs_mod.py -t raw - -t aprs -  | python aprs_demod.py -v -t raw -
```

The output here shows the reverse process of above.  In this case, NRZI is performed before the I show the demod frame.

```
# APRS DEMOD
# RATE 22050
# IN   raw -
# OUT  aprs -
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







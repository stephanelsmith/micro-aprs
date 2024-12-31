# Unix/Linux Port

Does the Micropython port require a custom firmware build?

No, building a custom firmware is not necessary for the Micropython port.  By default, tight loops are optimized with the [Viper emitter](https://docs.micropython.org/en/latest/reference/speed_python.html#the-viper-code-emitter) which provides a significant performance boost.

That said, it's a great idea to get next level performance with C optimized functions!

## Building Micropython Firware

[Official install instructions](https://github.com/micropython/micropython/tree/master/ports/unix).  In short:

```
git clone git@github.com:micropython/micropython.git
cd micropython
git submodule update --init --recursive
make -C mpy-cross
cd ports/unix
```

Build micropython with C modules
```
make USER_C_MODULES=~/micro-aprs/upy/c_modules
```

If using bash, link the micropython executable into your home/bin folder.
```
mkdir ~/bin
ln -sf ~/micropython/ports/unix/build-standard/micropython ~/bin/.
```

## Run examples

From the ```micro-aprs/src``` folder, try an example

* Decode [International Space Station flyby recording](https://inst.eecs.berkeley.edu/~ee123/sp14/lab3/ISSpkt.wav)
```
wget https://inst.eecs.berkeley.edu/~ee123/sp14/lab3/ISSpkt.wav
sox -t wav test/ISSpkt.wav -t raw -b 16 -e signed-integer -c 1 -r 22050 - | micropython aprs_demod.py -t -
```
```
RS0ISS>CQ:>ARISS - International Space Station
```


* Try piping APRS -> modulation -> demodulation
```
echo "KI5TOF>APRS:>hello world!" | micropython aprs_mod.py -v | micropython aprs_demod.py -v -t -
```
```
# APRS DEMOD
# RATE 22050
# IN   -
# OUT  -# APRS MOD

# RATE 22050
# IN   -
# OUT  -
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

* Try mixing micropython with python!
```
echo "KI5TOF>APRS:>hello world!" | micropython aprs_mod.py -v | python aprs_demod.py -v -t -
echo "KI5TOF>APRS:>hello world!" | python aprs_mod.py -v | micropython aprs_demod.py -v -t -
```

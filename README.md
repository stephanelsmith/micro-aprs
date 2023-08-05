


# Micro APRS MODEM

A python/micropython based library for encoding/decoding, modulating/demodulating APRS/AX.25 packets in AFSK.  

![AFSK hello world](docs/afsk_hello.png?raw=true "AFSK hello")

The purpose of this library is to thread-the-needle of both enabling APRS/AX.25/AFSK from PC to microcontroller while maintaining portability and readability of python.  This library is optimized for embedded systems, especially [micropython supported targets and platforms ](https://github.com/micropython/micropython#supported-platforms--architectures) and small computers, not to mention Cpython and Pypy!

In practice this means we:
* Avoid floating point and math libraries and dependencies in critical sections.  
	* :+1: Integer math only
	* :+1: Lookup tables 
	* :+1: No external libraries (numpy/scipy/pandas).
* Special care for memory allocation
	* :+1: Pre-computing buffer/array sizes and modifying in place
	* :+1: Using memoryview objects to pass slices to functions and modifying those slices in place
	* :-1: Dynamically appending items to a list
	* :-1: Functional programming style -> creating/returning new arrays instead of mutating in place
* Single threaded, multitask friendly
	* :+1::+1: Asyncio


## Tutorial

As many who've gone down this path have mentioned, there's really just not a lot of information out there covering these topics.  I hope these tutorial sections will provide you additional information on how it works: 
* [AFSK Demodulation](docs/demod/README.md)
* [AFSK Modulation](docs/mod/README.md)
* [AX25/APRS Encoding and Decoding](docs/encdec/README.md)


## Testing

The standards tested against are: 
* [DireWolf](https://github.com/wb2osz/direwolf)
* [Multimon-NG](https://github.com/EliasOenal/multimon-ng)

## APRS to AFSK Modulation

* mod.py provides conversion from APRS string(s) into raw 16 bit signed integer raw format with a default sampling rate 22050.  Special consideration taken:
	* Continuous waveform switching between mark and space frequencies.
	* NRZI encoding continuity between adjacent APRS messages
	* Verbose mode for complete, step-by-step modulation results
	* Programmable number of lead flags before first message (vox activation or assisting with demodulation).

* mod.py arguments and usage
	* -v, verbose mode.  Debugging information printed to stderr
	* -q, quiet mode. Stdout suppressed
	* -r, data rate. Default is 22050
	* -t <type> <source>, input format.  Currently only 'aprs' type is supported with input via stdin '-' or file.  Default is aprs strings from stdin.

* Mod with Multimon-ng Decode Example
```
echo "KI5TOF>APRS:hello world!" | python mod.py | multimon-ng -t raw -A -a AFSK1200 -
```
```
multimon-ng 1.1.9
(C) 1996/1997 by Tom Sailer HB9JNX/AE4WA
(C) 2012-2020 by Elias Oenal
Available demodulators: POCSAG512 POCSAG1200 POCSAG2400 FLEX EAS UFSK1200 CLIPFSK FMSFSK AFSK1200 AFSK2400 AFSK2400_2 AFSK2400_3 HAPN4800 FSK9600 DTMF ZVEI1 ZVEI2 ZVEI3 DZVEI PZVEI EEA EIA CCIR MORSE_CW DUMPCSV X10 SCOPE
Enabled demodulators: AFSK1200
APRS: KI5TOF>APRS:hello world!
```

* Mod with Direwolf Decode Example
```
echo "KI5TOF>APRS:hello world!" | python mod.py -v | sox -t raw -b 16 -e signed-integer -c 1 -v 7 -r 22050 -  -t wav test.wav
atest test.wav
```
```
22050 samples per second.  16 bits per sample.  1 audio channels.
10112 audio bytes in file.  Duration = 0.2 seconds.
Fix Bits level = 0
Channel 0: 1200 baud, AFSK 1200 & 2200 Hz, E, 22050 sample rate.

DECODED[1] 0:00.225 KI5TOF audio level = 55(29/29)
[0] KI5TOF>APRS:hello world!
```

* Modulation verbose mode
```
echo "KI5TOF>APRS:hello world!" | python mod.py -v -q
```
```
===== MOD >>>>> KI5TOF>APRS:hello world!
--ax25--
0000  7e 82 a0 a4 a6 40 40 60 96 92   01111110 10000010 10100000 10100100 10100110 01000000 01000000 01100000 10010110 10010010   ~ ¤¦@@`
0010  6a a8 9e 8c 61 03 f0 68 65 6c   01101010 10101000 10011110 10001100 01100001 00000011 11110000 01101000 01100101 01101100   j¨aðhel
0020  6c 6f 20 77 6f 72 6c 64 21 ff   01101100 01101111 00100000 01110111 01101111 01110010 01101100 01100100 00100001 11111111   lo world!ÿ
0030  07 7e -- -- -- -- -- -- -- --   00000111 01111110 -------- -------- -------- -------- -------- -------- -------- --------   ~--------
-reversed-
0000  7e 41 05 25 65 02 02 06 69 49   01111110 01000001 00000101 00100101 01100101 00000010 00000010 00000110 01101001 01001001   ~A%eiI
0010  56 15 79 31 86 c0 0f 16 a6 36   01010110 00010101 01111001 00110001 10000110 11000000 00001111 00010110 10100110 00110110   Vy1À¦6
0020  36 f6 04 ee f6 4e 36 26 84 ff   00110110 11110110 00000100 11101110 11110110 01001110 00110110 00100110 10000100 11111111   6öîöN6&ÿ
0030  e0 7e 00 00 00 00 00 00 00 00   11100000 01111110 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000   à~
-bit stuffed-
0000  7e 41 05 25 65 02 02 06 69 49   01111110 01000001 00000101 00100101 01100101 00000010 00000010 00000110 01101001 01001001   ~A%eiI
0010  56 15 79 31 86 c0 0f 16 a6 36   01010110 00010101 01111001 00110001 10000110 11000000 00001111 00010110 10100110 00110110   Vy1À¦6
0020  36 f6 04 ee f6 4e 36 26 84 fb   00110110 11110110 00000100 11101110 11110110 01001110 00110110 00100110 10000100 11111011   6öîöN6&û
0030  e8 1f 80 00 00 00 00 00 00 00   11101000 00011111 10000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000   è
--nrzi-- bits 258 bytes 32 remain 2
11111110 11010100 10101100 10010011 00010011 01010110 10101001 01010001 00011011 00100100
11001110 10110011 00000100 10001011 10101110 00101010 10100000 10110001 10010001 01110001
01110001 11110001 01010010 00011110 00001110 11011110 10001110 10010001 10101101 11111000
00011010 10111111 10
```


## AFSK Demodulation to APRS Strings

* demod.py reads in raw 16 bit signed integers from standard input or file and output detected APRS strings:
	* Verbose mode for complete, step-by-step modulation resultsdemodulation).

* demod arguments and usage:
	* -v, verbose mode.  Debugging information printed to stderr
	* -r, data rate. Default is 22050
	* -t <type> <source>, input format.  Currently only 'raw' type is supported with input via stdin '-' or file.  Default is raw from stdin.
	
* Demodulation in verbose step-by-step mode
```
echo "KI5TOF>APRS:hello world!" | python mod.py | python demod.py -v -t raw -
```
```
frame
===== DEMOD frame ======
0000  7e 41 05 25 65 02 02 06 69 49   01111110 01000001 00000101 00100101 01100101 00000010 00000010 00000110 01101001 01001001   ~A%eiI
0010  56 15 79 31 86 c0 0f 16 a6 36   01010110 00010101 01111001 00110001 10000110 11000000 00001111 00010110 10100110 00110110   Vy1À¦6
0020  36 f6 04 ee f6 4e 36 26 84 fb   00110110 11110110 00000100 11101110 11110110 01001110 00110110 00100110 10000100 11111011   6öîöN6&û
0030  e8 1f 80 -- -- -- -- -- -- --   11101000 00011111 10000000 -------- -------- -------- -------- -------- -------- --------   è-------
-un-stuffed-
0000  7e 41 05 25 65 02 02 06 69 49   01111110 01000001 00000101 00100101 01100101 00000010 00000010 00000110 01101001 01001001   ~A%eiI
0010  56 15 79 31 86 c0 0f 16 a6 36   01010110 00010101 01111001 00110001 10000110 11000000 00001111 00010110 10100110 00110110   Vy1À¦6
0020  36 f6 04 ee f6 4e 36 26 84 ff   00110110 11110110 00000100 11101110 11110110 01001110 00110110 00100110 10000100 11111111   6öîöN6&ÿ
0030  e0 7e 00 -- -- -- -- -- -- --   11100000 01111110 00000000 -------- -------- -------- -------- -------- -------- --------   à~-------
-un-reversed-
0000  7e 82 a0 a4 a6 40 40 60 96 92   01111110 10000010 10100000 10100100 10100110 01000000 01000000 01100000 10010110 10010010   ~ ¤¦@@`
0010  6a a8 9e 8c 61 03 f0 68 65 6c   01101010 10101000 10011110 10001100 01100001 00000011 11110000 01101000 01100101 01101100   j¨aðhel
0020  6c 6f 20 77 6f 72 6c 64 21 ff   01101100 01101111 00100000 01110111 01101111 01110010 01101100 01100100 00100001 11111111   lo world!ÿ
0030  07 7e 00 -- -- -- -- -- -- --   00000111 01111110 00000000 -------- -------- -------- -------- -------- -------- --------   ~-------
KI5TOF>APRS:hello world!
```

* Decode Direwolf generated sample
```
gen_packets -r 22050 -o x.wav
sox -t wav x.wav -t raw -b 16 -e signed-integer -c 1 -r 22050 - | python demod.py -t raw -
```
```
WB2OSZ-11>TEST:,The quick brown fox jumps over the lazy dog!  1 of 4
WB2OSZ-11>TEST:,The quick brown fox jumps over the lazy dog!  2 of 4
WB2OSZ-11>TEST:,The quick brown fox jumps over the lazy dog!  3 of 4
WB2OSZ-11>TEST:,The quick brown fox jumps over the lazy dog!  4 of 4
```

* Decode [International Space Station flyby recording](https://inst.eecs.berkeley.edu/~ee123/sp15/lab/lab6/Lab6_Part_B-APRS.html)
```
wget https://inst.eecs.berkeley.edu/~ee123/sp14/lab3/ISSpkt.wav
sox -t wav ISSpkt.wav -t raw -b 16 -e signed-integer -c 1 -r 22050 - | python demod.py -t raw -
```
```
RS0ISS>CQ:>ARISS - International Space Station
```

* Decode [TNC Test CD](http://wa8lmf.net/TNCtest/)
    * Download and convert TNC tests to .wav/.flac files
    * Using bchunk (apt-get install bchunk)
```
wget http://wa8lmf.net/TNCtest/TNC_Test_CD_Ver-1.1.zip
bchunk -w TNC_Test_Ver-1.1.bin TNC_Test_Ver-1.1.cue tnc_test
find -name "*wav" | xargs basename -s .wav | xargs -i sox -t wav {}.wav -t raw -b 16 -e signed-integer -c 1 -r 22050 {}.raw
```
    * Run track 2 test
```
sox -t wav test/tnc_test02.wav -t raw -b 16 -e signed-integer -c 1 -r 22050 - | python demod.py -t raw -
python demod.py -t raw test/tnc_test02.raw
```



## References and Acknowledgments

AX25 encoding and decoding references were not as easy to come by as I expected considering the standard.  I hope the full verbose output provided by this utility will assist others.  A few references were particularly helpful
* [Direwolf packet assembler](https://github.com/wb2osz/direwolf/blob/master/src/ax25_pad.c)
* [Infineon Simplifed FSK Detection App Note](https://www.infineon.com/dgdl/Infineon-AN2336_PSoC_1_Simplified_FSK_Detection-ApplicationNotes-v07_00-EN.pdf?fileId=8ac78c8c7cdc391c017d07237cdd46c0)
* [AFSK Digital Correlator Demodulator](https://notebooks.githubusercontent.com/view/ipynb?browser=chrome&color_mode=auto&commit=18914893d0853070788a37d986bbd58db08721aa&device=unknown&enc_url=68747470733a2f2f7261772e67697468756275736572636f6e74656e742e636f6d2f6d6f62696c696e6b642f6166736b2d64656d6f64756c61746f722f313839313438393364303835333037303738386133376439383662626435386462303837323161612f6166736b2d64656d6f64756c61746f722e6970796e62&logged_in=false&nwo=mobilinkd%2Fafsk-demodulator&path=afsk-demodulator.ipynb&platform=android&repository_id=175103461&repository_type=Repository&version=98)




## License
MIT License


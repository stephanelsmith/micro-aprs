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


### **Micro-Aprs decodes 1000+ error-free frames on the [TNC CD Track 2](http://wa8lmf.net/TNCtest/).  That's **1010** :eyes: in a balanced mode at **1020** :fireworks: in a more computational intensive mode!**  (TNC CD Track 2 is the universal test for APRS demod, [this performance is very good!](https://github.com/wb2osz/direwolf/blob/dev/doc/WA8LMF-TNC-Test-CD-Results.pdf))


## :mortar_board: Tutorials
As many who've gone down this path have mentioned, there's surprisingly little useful information out there covering these topics.  I hope these tutorial sections will provide you additional information on getting started!
* [AFSK Demodulation](docs/demod/README.md). Convert raw AFSK samples to bits.
* [AFSK Modulation](docs/mod/README.md). Convert byte arrays to AFSK samples
* [AX25/APRS Encoding and Decoding](docs/encdec/README.md). Step-by-step encoding/decoding APRS and AX25.
* [144.39MHz 1/4 Wave Ground Plane Antenna Design](docs/ant/README.md).


## :horse_racing: **Start here!**
Basic command line for encoding and APRS strings to AFSK audio samples and the reverse.
* [Encode](docs/ports/mod/README.md) APRS strings to AFSK audio samples.
* [Decode](docs/ports/demod/README.md) AFSK audio samples to APRS strings.
* [Micropython](docs/ports/upy/README.md) Encode/decode, but with embedded system friendly (also great on big machines too!).
* [Pypy](docs/ports/pypy/README.md), another supported options faster than C python.

## :desktop_computer: Application examples
Applications using ```aprs_mod.py``` and ```aprs_demod.py```.
* [SDR (rtl_fm) based live decode](docs/ports/sdr/README.md).
* [SDR (rtl_fm) based RX only Igate](docs/ports/sdrigate/README.md).
* [HT/Android APRS beacon](docs/ports/termux/README.md).

## :pager: Embedded ports and examples
With Micropython, these examples show some examples for embedded systems.  I primarily target ESP32-S3 at the moment.
* [ESP32-S3 - working around missing DAC](docs/ports/dac/README.md)
* [TinyS3](docs/ports/tinys3/README.md), a quality and accessible esp32s3 board.
* [LilyGo T-TWR Plus](docs/ports/lilygottwr/README.md), a commerically available esp32s3 board with SA868 Wireless Transceiver.


## :bulb: Future Work
* Rx/Tx digipeating
* Deploy as a :balloon: [HAB](https://amateur.sondehub.org/) payload!

## :raised_hands: Acknowledgements
- [Micropython](https://github.com/micropython/micropython) project
- [Direwolf TNC](https://github.com/wb2osz/direwolf)


## License
GNU General Public License v3.0



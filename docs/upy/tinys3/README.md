
# TinyS3

The purpose of this port is
- A minimalist example of generating an AFSK waveform on an output pin
- A starting point for porting to other platforms

I've chosen to use [TinyS3](https://unexpectedmaker.com/shop.html#!/TinyS3/p/577100101/category=154217256) because is uses the ESP32S3 chip, it's tiny, versatile, easy to purchase, and I have a drawer full of them!  The [ESP32S3 chip by Espressif](https://www.espressif.com/en/products/socs/esp32-s3) is a 250MHz dual-core embedded proessor with built-in wifi, bluetooth, and usb support.  The TinyS3 adds 8Mb flash, 8Mb ram and pretty much everything else you need for a project.  TinyS3 is available through [UnexpectedMaker's store](https://unexpectedmaker.com/) directy, Mouser Digkey, Sparkfun and others. He's got tons of other great boards to check out to!

Finally, ESP32S3 is a great choice because the [LilyGo T-Twr port](../lilygottwr/README.md) also uses the esp32s3 (and also includes the radio!)


## Building Micropython Firware for TinyS3

```
git clone git@github.com:micropython/micropython.git
cd micropython
git submodule update --init --recursive
make -C mpy-cross
cd ports/esp32
```

Add the APRS board file
```
ln -sf ~/micro-aprs/upy/boards/SS_APRS boards/.
```

Build micropython port with C modules
```
make BOARD=SS_APRS USER_C_MODULES=~/micro-aprs/c_modules/esp32s3.cmake
```

Flash the esp32 chip
```
py -m esptool --chip esp32s3 --port COM13 write_flash -z 0 .\micropython\ports\esp32\build-SS_APRS\firmware.bin
```



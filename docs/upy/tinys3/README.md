<p>
<img src="tinys3-logo.png?raw=true" alt="" width="300">  
</p>

The purpose of this port is
- A "hello world" of building and running custom micropython on an ESP32S3 board.
- A minimalist example of generating an AFSK waveform on an output pin
- A starting point for porting to other embedded platforms

I've chosen to use [TinyS3](https://unexpectedmaker.com/shop.html#!/TinyS3/p/577100101/category=154217256) because is uses the ESP32S3 chip, it's tiny, versatile, easy to purchase, and I have a drawer full of them!  The [ESP32S3 chip by Espressif](https://www.espressif.com/en/products/socs/esp32-s3) is a 240MHz dual-core embedded proessor with built-in wifi, bluetooth, and usb support.  The TinyS3 adds 8Mb flash, 8Mb ram and pretty much everything else you need for a project.  TinyS3 is available through [UnexpectedMaker's store](https://unexpectedmaker.com/) directy, Mouser Digkey, Sparkfun and others. He's got tons of other great boards to check out to!

Finally, ESP32S3 is a great choice because the [LilyGo T-Twr port](../lilygottwr/README.md) also uses the esp32s3 (and also includes the radio!)


## Building Micropython Firware for TinyS3

Clone the Espressif ESP-IDF repo
```
git clone --depth 1 --branch v5.2.2 https://github.com/espressif/esp-idf.git esp-idf-v5.2.2
cd esp-idf-v5.2.2
git submodule update --init --recursive
./install.sh
source export.sh
```
From here on, you will need to source export.sh to setup your environment.

Now clone the Micropython repo
```
git clone git@github.com:micropython/micropython.git
cd micropython
git submodule update --init --recursive
make -C mpy-cross
cd ports/esp32
```
From here, the commands assume the current working directory is ```micropython/ports/esp32```.

Add the APRS board file
```
ln -sf ~/micro-aprs/upy/boards/SS_APRS boards/.
```

Build micropython port with C modules
```
make BOARD=SS_APRS USER_C_MODULES=~/micro-aprs/c_modules/esp32s3.cmake
```

A vanilla TinyS3 board is already included in the Micropython project.  To build it, try
```
make BOARD=UM_TINYS3
```


Flash the esp32 chip.  Before flashing the ESP32S3 needs to be in the bootloader.  This is done by holding the ```boot``` button and clicking ```reset```.  You can find the right comm port with ```py -m serial.tools.list_ports```.  You may need to ```py -m pip install pyserial``` first.
```
py -m esptool --chip esp32s3 --port COM13 write_flash -z 0 .\build-SS_APRS\firmware.bin
```
Finally, click ```reset``` again to begin execution.


## Trying the TinyS3 Port

Fire up a terminal
```
py -m serial.tools.miniterm COM18
```

Start afsk "hello world" example
```
import tinys3
```

The output is on Pin 1.


# Building Micropython Firware

## Embedded Ports (ESP32)

[Official esp32 instructions](https://github.com/micropython/micropython/tree/master/ports/unix).  In short:

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






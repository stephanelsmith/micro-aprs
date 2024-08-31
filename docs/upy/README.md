# Building Micropython Firware

## Does the Micropython port require a custom firmware build?

No, building a custom firmware is not necessary for the Micropython port.  By default, tight loops are optimized with the [Viper emitter](https://docs.micropython.org/en/latest/reference/speed_python.html#the-viper-code-emitter) which provides a significant performance boost.

That said, there are many benefits to a custom Micropython build:
- Next level performance with C optimized functions
- Byte frozen code for faster load/start time
- Easier (in my opinion) code iteration


## Unix Port

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






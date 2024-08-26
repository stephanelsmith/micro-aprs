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
make USER_C_MODULES=/home/ssmith/micro-aprs/upy/c_modules
make USER_C_MODULES=/home/ssmith/micro-aprs/upy/c_modules FROZEN_MANIFEST=/home/ssmith/micro-aprs/upy/unix_manifest.py
```

```
ln -sf ~/micropython/ports/unix/build-standard/micropython .
```

## Embedded Ports (ESP32)




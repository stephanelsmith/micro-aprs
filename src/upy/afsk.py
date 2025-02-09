
import sys
from micropython import const
import asyncio
from array import array
from machine import Timer
from asyncio import ThreadSafeFlag

# from afsk.func_viper import create_power_meter
from afsk.fir_options import fir_options
from lib.memoize import memoize_loads

_AFSK_IN_SQLCH_LEVEL = const(100)
_FMARK  = 1200
_FSPACE = 2200

async def in_afsk(adc, rio, fs = 11_025):
    try:
        tsf = ThreadSafeFlag()
        tim = Timer(1)

        def cb(tim):
            nonlocal adc, rio
            o = adc.read_u16()
            rio.write(o.to_bytes(2))

        tim.init(freq=fs, mode=Timer.PERIODIC, callback=cb)
        await tsf.wait()
    except Exception as err:
        sys.print_exception(err)
    finally:
        tim.deinit()

async def out_afsk(pwm, 
                   arr, 
                   siz, 
                   fout = 11_025,
                   ):
    try:
        tsf = ThreadSafeFlag()
        tim = Timer(1)

        # viper nonlocals
        nl = array('H', [0,])

        @micropython.viper
        def cb(tim):
            nonlocal nl,pwm,arr,siz,tsf
            _nl  = ptr16(nl)  # uint
            _arr = ptr16(arr) # uint
            i:int = _nl[0]
            if i < int(siz):
                pwm.duty_u16(_arr[i])
                i += 1
            if i == int(siz):
                tsf.set()
                i += 1 # > int size we are done
            _nl[0] = i

        tim.init(freq=fout, mode=Timer.PERIODIC, callback=cb)
        await tsf.wait()
    except Exception as err:
        sys.print_exception(err)
    finally:
        tim.deinit()

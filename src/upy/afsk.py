
import sys
from micropython import RingIO
from micropython import const
import asyncio
from array import array
from machine import Timer
from asyncio import ThreadSafeFlag

from afsk.func_viper import create_power_meter

_AFSK_IN_SQLCH_LEVEL = const(100)

async def in_afsk(adc, rio, fin = 11_025):
    try:
        tsf = ThreadSafeFlag()
        tim = Timer(1)
        pwrmtr = create_power_meter(siz = fin//1200*8)
        sig = False

        def cb(tim):
            nonlocal adc, rio, sig
            u = adc.read_u16()
            s = u - 32768 # convert u16 to s16
            o = pwrmtr(s)
            if sig and o < _AFSK_IN_SQLCH_LEVEL:
                tsf.set()
            sig = o > _AFSK_IN_SQLCH_LEVEL
            if sig:
                rio.write(u.to_bytes(2))
        tim.init(freq=fin, mode=Timer.PERIODIC, callback=cb)
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


import sys
import asyncio
import gc
from array import array

from machine import Pin, PWM
from machine import Timer

from asyncio import Event
from asyncio import ThreadSafeFlag
from micropython import const

from lib.compat import Queue

from afsk.mod import AFSKModulator
from ax25.ax25 import AX25

import lib.upydash as _

# pwm frequency
_FPWM = const(500_000)

# afsk sample frequency
# _FOUT = const(11_025)
_FOUT = const(22_050)
# _FOUT = const(44_100)

_AFSK_OUT_PIN = const(1)
_AFSK_PTT_PIN = const(9)

async def gc_coro():
    try:
        while True:
            gc.collect()
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        raise
    except Exception as err:
        sys.print_exception(err)

async def out_afsk(arr, siz):

    try:
        tsf = ThreadSafeFlag()
        pwm = PWM(Pin(_AFSK_OUT_PIN), freq=_FPWM, duty_u16=0) # resolution = 26.2536 - 1.4427 log(fpwm)
        tim = Timer(1)

        nl = array('H', [0,]) # viper nonlocals

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

        tim.init(freq=_FOUT, mode=Timer.PERIODIC, callback=cb)
        await tsf.wait()
    except Exception as err:
        sys.print_exception(err)
    finally:
        tim.deinit()
        pwm.deinit()

async def start():

    try:
        gc_task = asyncio.create_task(gc_coro())
        ptt = Pin(_AFSK_PTT_PIN, mode = Pin.OUT, value = 0)

        async with AFSKModulator(sampling_rate = _FOUT,
                                 signed        = False,
                                 verbose       = False) as afsk_mod:
            aprs = b'KI5TOF>APRS:>hello world!'
            ax25 = AX25(aprs    = aprs,
                        verbose = False,)
            #AFSK
            afsk,stop_bit = ax25.to_afsk()
            # print(afsk)

            await afsk_mod.pad_zeros(ms = 10)
            await afsk_mod.send_flags(10)
            await afsk_mod.to_samples(afsk     = afsk, 
                                      stop_bit = stop_bit,
                                      )
            await afsk_mod.send_flags(2)
            await afsk_mod.pad_zeros(ms = 10)
            arr,siz = await afsk_mod.flush()

        x = 0
        while True:
            try:
                ptt.value(1)
                await out_afsk(arr, siz)
                print('loop {}'.format(x))
                x += 1
            finally:
                ptt.value(0)

    except Exception as err:
        sys.print_exception(err)
    finally:
        gc_task.cancel()

def main():
    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        pass
    except Exception as err:
        sys.print_exception(err)
    finally:
        asyncio.new_event_loop()  # Clear retained state
main()

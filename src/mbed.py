
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

_FPWM = const(500_000)
_FOUT = const(22_050)

async def gc_coro():
    try:
        while True:
            gc.collect()
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        raise
    except Exception as err:
        sys.print_exception(err)

def closure_cb(pwm, arr, siz, done):
    nl = array('H', [0,])
    @micropython.viper
    def cb(t):
        nonlocal nl,pwm,arr,siz,done
        _nl  = ptr16(nl)  # uint
        _arr = ptr16(arr) # uint
        i:int = _nl[0]
        pwm.duty_u16(_arr[i])
        i+=1
        if i == int(siz):
            done.set()
        _nl[0] = i
    return cb

async def start():

    try:
        gc_task = asyncio.create_task(gc_coro())

        async with AFSKModulator(sampling_rate = _FOUT,
                                 signed        = False,
                                 verbose       = False) as afsk_mod:
            aprs = b'KI5TOF>APRS:>hello world!'
            ax25 = AX25(aprs    = aprs,
                        verbose = False,)
            #AFSK
            afsk,stop_bit = ax25.to_afsk()
            # print(afsk)

            await afsk_mod.send_flags(4)
            #generate samples
            await afsk_mod.to_samples(afsk     = afsk, 
                                        stop_bit = stop_bit,
                                        )
            await afsk_mod.send_flags(4)
            arr,siz = await afsk_mod.flush()

        pwm = PWM(Pin(1), freq=_FPWM, duty_u16=0) # resolution = 26.2536 - 1.4427 log(fpwm)
        tsf = ThreadSafeFlag()
        tim1 = Timer(1)
        tim1.init(freq=_FOUT, mode=Timer.PERIODIC, callback=closure_cb(pwm, arr, siz, tsf))
        await tsf.wait()
        print('DONE')
        await asynio.sleep_ms(1)
        tim1.deinit()
        await asynio.sleep_ms(1)
        pwm.deinit()

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

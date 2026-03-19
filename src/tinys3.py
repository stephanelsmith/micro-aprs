
import sys
import asyncio
import gc

from machine import Pin, PWM, Timer

from asyncio import Event
from micropython import const

from lib.compat import Queue

from afsk.mod import AFSKModulator
from ax25.ax25 import AX25

import lib.upydash as _

from upy.afsk import out_afsk

# pwm frequency
_FPWM = const(500_000)

# afsk sample frequency
_FOUT = const(11_025)
# _FOUT = const(22_050)
# _FOUT = const(44_100)

_AFSK_OUT_PIN = const(1)

async def gc_coro():
    try:
        while True:
            gc.collect()
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        raise
    except Exception as err:
        sys.print_exception(err)

async def start():

    try:
        pwm = PWM(Pin(_AFSK_OUT_PIN), freq=_FPWM, duty_u16=0) # resolution = 26.2536 - 1.4427 log(fpwm)
        gc_task = asyncio.create_task(gc_coro())

        async with AFSKModulator(sampling_rate = _FOUT,
                                 signed        = False,
                                 verbose       = False) as afsk_mod:
            x = 0
            while True:
                aprs = b'KI5TOF>APRS:>hello world {}'.format(x)
                ax25 = AX25(aprs    = aprs,
                            verbose = False,)
                #AFSK
                afsk,stop_bit = ax25.to_afsk()

                await afsk_mod.pad_zeros(ms = 10)
                await afsk_mod.send_flags(10)
                await afsk_mod.to_samples(afsk     = afsk, 
                                        stop_bit = stop_bit,
                                        )
                await afsk_mod.send_flags(2)
                await afsk_mod.pad_zeros(ms = 10)
                arr,siz = await afsk_mod.flush()

                print(aprs)
                await out_afsk(pwm, arr, siz, _FOUT)
                x += 1
                await asyncio.sleep_ms(5000)

    except Exception as err:
        sys.print_exception(err)
    finally:
        pwm.deinit()
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


import sys
import asyncio
import gc
# import time

from array import array
from asyncio import Event
from micropython import RingIO
from machine import ADC
from machine import Pin

from lib.compat import Queue

from afsk.mod import AFSKModulator
from ax25.ax25 import AX25
from afsk.demod import AFSKDemodulator
from ax25.from_afsk import AX25FromAFSK
from afsk.func import afsk_detector
from upy.afsk import out_afsk
from cdsp import i16tobs

import lib.upydash as _
from lib.compat import print_exc

# afsk sample frequency
_FOUT = 11_025
# _FOUT = const(22_050)
# _FOUT = const(44_100)

_AFSK_IN_PIN = const(2)

@micropython.viper
def in_afsk(adc, rio, demod):
    bpf = demod.bpf
    pwrmtr = demod.pwrmtr
    sql:int = int(demod.squelch)
    isin:int = int(0)
    # read = adc.read
    read = adc.read_u16
    write = rio.write
    while True:
        o:int = int(read())
        o:int = int(bpf(o))
        p:int = int(pwrmtr(o))
        # print(o,p)
        if p > sql  and not isin:
            isin = 1
        elif p < sql and isin:
            return 
        write(i16tobs(o))

async def start():

    tasks = []
    try:
        ax25_q = Queue()
        rio = RingIO(500000)

        adc = ADC(Pin(_AFSK_IN_PIN, Pin.IN))

        bits_q = Queue()
        async with AFSKDemodulator(sampling_rate = _FOUT,
                                   in_rx         = None,   # don't launch core task
                                   stream_type   = 'u16',
                                   bits_out_q    = bits_q,
                                   is_embedded   = True,
                                   options       = {},
                                   verbose       = False,
                                   ) as demod:
            async with AX25FromAFSK(bits_in_q      = bits_q,
                                    ax25_q         = ax25_q,
                                    verbose        = False):
                while True:
                    # synchronous read from ADC
                    in_afsk(adc, rio, demod)
                    print('READ: {}'.format(rio.any()))

                    if rio.any() == 0:
                        break

                    # process results
                    await demod.stream_core(in_rx = rio)

                    # process ax25
                    while not ax25_q.empty():
                        ax25 = await ax25_q.get()
                        print(ax25)

                    # clean up
                    gc.collect()

        await asyncio.gather(*tasks, return_exceptions=True)

    except asyncio.CancelledError:
        raise
    except KeyboardInterrupt:
        return
    except Exception as err:
        print_exc(err)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*[t for t in tasks if not t.done()], return_exceptions=True)


def main():
    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        pass
    except Exception as err:
        print_exc(err)
    finally:
        asyncio.new_event_loop()  # Clear retained state
main()

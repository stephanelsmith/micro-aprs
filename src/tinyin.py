
import sys
import asyncio
import gc
import time

from array import array
from asyncio import Event
from micropython import RingIO
from machine import ADC
from machine import Pin
from machine import Timer
from asyncio import ThreadSafeFlag
from asyncio import Lock
import uctypes

from lib.compat import Queue

from afsk.mod import AFSKModulator
from ax25.ax25 import AX25
from afsk.demod import AFSKDemodulator
from ax25.from_afsk import AX25FromAFSK
from upy.afsk import out_afsk
from afsk.func import create_power_meter

from cdsp import i16tobs
from cdsp import utoi32
from cdsp import utoi16
from cdsp import isqrt

import lib.upydash as _

# afsk sample frequency
_FOUT = 11_025
# _FOUT = const(22_050)
# _FOUT = const(44_100)

_AFSK_IN_PIN = const(2)
_DEBUG_OUT_PIN = const(6)

from cdsp import tim_cb

class TimCB:
    def __init__(self, adc, do, rio, tim):
        self.tog = do.toggle
        self.read = adc.read_u16
        self.write = rio.write
        self.deinit = tim.deinit
        self.tim = tim

        self.buf = bytearray(2)
        self.state = 0
        self.cnt = 0 # count the number of iterations
        self.arr = array('i', [0 for x in range(50)]) # the buffer
        self.idx = 0 # indexing position

    def reset(self, tsf):
        self.tsfset = tsf.set
        self.state = 0
        self.cnt = 0 # count the number of iterations
        self.idx = 0 # indexing position

    def __call__(self, timer):
        # if not tim_cb(self):
            # timer.deinit()
        tim_cb(self)

async def in_afsk(timcb):
    tsf = ThreadSafeFlag()
    timcb.reset(tsf = tsf)
    tim = timcb.tim
   
    try:
        tim.init(mode=Timer.PERIODIC, freq=_FOUT, callback=timcb)
        await tsf.wait()
    except Exception as err:
        sys.print_exception(err)
    finally:
        tim.deinit()


async def start():

    tasks = []
    try:
        ax25_q = Queue()
        rio = RingIO(20_000)

        adc = ADC(Pin(_AFSK_IN_PIN, Pin.IN))
        do = Pin(_DEBUG_OUT_PIN, Pin.OUT)
        tim = Timer(1)
        lck = Lock()

        timcb = TimCB(adc    = adc,
                      do     = do,
                      rio    = rio,
                      tim    = tim)

        bits_q = Queue()
        async with AFSKDemodulator(sampling_rate = _FOUT,
                                   in_rx         = None,   # don't launch core task
                                   stream_type   = 's16',
                                   bits_out_q    = bits_q,
                                   is_embedded   = True,
                                   options       = {},
                                   verbose       = False,
                                   ) as demod:
            async with AX25FromAFSK(bits_in_q      = bits_q,
                                    ax25_q         = ax25_q,
                                    verbose        = False):

                # warmup
                # rio.write(b'\x7f'*10000)

                while True:
                    # synchronous read from ADC
                    # print(0)
                    print('top')
                    if rio.any() == 0:
                        async with lck:
                            await in_afsk(timcb)
                        # rio.write(b'\x7f'*1000)
                        await asyncio.sleep_ms(10)
                    print('READ: {}'.format(rio.any()))

                    # if rio.any() == 0:
                        # break
                    # print(1)

                    # process results
                    print('demod')
                    await demod.stream_core(in_rx = rio)
                    await demod.join()
                    await bits_q.join()
                    # print(2)

                    # process ax25
                    while not ax25_q.empty():
                        # print(3)
                        ax25 = await ax25_q.get()
                        print(ax25)
                    # print(4)

                    # clean up
                    print('collect')
                    gc.collect()
                    await asyncio.sleep_ms(100)

        await asyncio.gather(*tasks, return_exceptions=True)

    except asyncio.CancelledError:
        raise
    except KeyboardInterrupt:
        return
    except Exception as err:
        sys.print_exception(err)
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
        sys.print_exception(err)
    finally:
        asyncio.new_event_loop()  # Clear retained state
main()


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
from cdsp import isqrt

import lib.upydash as _

# afsk sample frequency
_FOUT = 11_025
# _FOUT = const(22_050)
# _FOUT = const(44_100)

_AFSK_IN_PIN = const(2)
_DEBUG_OUT_PIN = const(6)

cReadi16 = {
    'i16'    : 0  | uctypes.INT16,
}

async def in_afsk(adc, rio, demod, do):
    pwrmtr = create_power_meter(siz = 20)

    read = adc.read_u16
    write = rio.write
    stdout = sys.stdout.write

    # pre-allocate read/write buffer
    buf = bytearray(uctypes.sizeof(cReadi16))
    stu = uctypes.struct(uctypes.addressof(buf),  cReadi16, uctypes.LITTLE_ENDIAN)

    tsf = ThreadSafeFlag()
    tim = Timer(1)
    tog = do.toggle

    isin:int = 0

    # closure params saved as array
    # _c = array('i',[0,10,])
    # _arr = array('i', (0 for x in range(10)))

    try:
        @micropython.viper
        def cb(tim):
            _o:int = int(read()) # read from adc
            stu.i16 = _o
            write(buf)
            tog() # debug
            _p:int = int(pwrmtr(_o))
            if _p >= 300:
                isin = 3 # HACK OBJECT VALUE = 1 ... (1<<1)|1
            elif int(isin):
                tsf.set()
        tim.init(mode=Timer.PERIODIC, freq=_FOUT, callback=cb)
        await tsf.wait()

    except Exception as err:
        sys.print_exception(err)
    finally:
        tim.deinit()


async def start():

    tasks = []
    try:
        ax25_q = Queue()
        rio = RingIO(100000)

        adc = ADC(Pin(_AFSK_IN_PIN, Pin.IN))
        do = Pin(_DEBUG_OUT_PIN, Pin.OUT)

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
                    await in_afsk(adc, rio, demod, do)
                    print('READ: {}'.format(rio.any()))

                    if rio.any() == 0:
                        break
                    print(1)

                    # process results
                    await demod.stream_core(in_rx = rio)
                    print(2)

                    # process ax25
                    while not ax25_q.empty():
                        print(3)
                        ax25 = await ax25_q.get()
                        print(ax25)
                    print(4)

                    # clean up
                    gc.collect()

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
